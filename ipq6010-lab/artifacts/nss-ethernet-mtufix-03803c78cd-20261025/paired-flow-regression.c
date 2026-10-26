
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GFP_KERNEL 0
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define READ_ONCE(x) (x)
#define guard(type) mock_guard
static void mock_guard(void *p) {(void)p;}
struct list_head {struct list_head *next,*prev;};
static void INIT_LIST_HEAD(struct list_head *h){h->next=h->prev=h;}
static void list_add_tail(struct list_head *n,struct list_head *h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static void list_del(struct list_head *n){n->prev->next=n->next;n->next->prev=n->prev;}
#define list_for_each_entry(p,h,m) for(p=container_of((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=container_of((p)->m.next,__typeof__(*p),m))
#define list_for_each_entry_safe(p,n,h,m) for(p=container_of((h)->next,__typeof__(*p),m),n=container_of((p)->m.next,__typeof__(*p),m);&(p)->m!=(h);p=n,n=container_of((n)->m.next,__typeof__(*n),m))
static int fail_alloc;
static void *kzalloc(size_t n,int flags){(void)flags;if(fail_alloc){fail_alloc=0;return NULL;}return calloc(1,n);}
#define kfree free
struct net_device {int refs;};
static void dev_hold(struct net_device *d){assert(d);d->refs++;}
static void dev_put(struct net_device *d){assert(d&&d->refs>1);d->refs--;}
enum {FLOW_ACTION_REDIRECT=1};
enum {FLOW_CLS_REPLACE=1,FLOW_CLS_DESTROY,FLOW_CLS_STATS};
enum tc_setup_type {TC_SETUP_CLSFLOWER=1};
struct flow_block {int id;};
struct flow_offload_tuple {unsigned char dir;};
struct flow_offload_tuple_rhash {struct flow_offload_tuple tuple;};
struct flow_offload {struct flow_offload_tuple_rhash tuplehash[2];};
struct flow_dissector {unsigned int value;};
struct nf_flow_key {unsigned int value[8];};
struct flow_match {struct flow_dissector *dissector;void *key,*mask;};
struct flow_action_entry {int id;struct net_device *dev;};
struct flow_action {unsigned int num_entries;struct flow_action_entry entries[];};
struct flow_rule {struct flow_match match;struct flow_action action;};
struct nf_flow_match {struct flow_dissector dissector;struct nf_flow_key key,mask;};
struct nf_flow_rule {struct nf_flow_match match;struct flow_rule *rule;};
struct flow_cls_offload {struct {void *extack;} common;int command;unsigned long cookie;struct flow_rule *rule;};
#define flow_action_for_each(i,a,f) for(i=0;i<(int)(f)->num_entries&&((a)=&(f)->entries[i],1);i++)
static struct flow_rule *flow_rule_alloc(unsigned int n){struct flow_rule *r=calloc(1,sizeof(*r)+n*sizeof(struct flow_action_entry));if(r)r->action.num_entries=n;return r;}
static struct flow_rule *flow_cls_offload_flow_rule(struct flow_cls_offload *c){return c->rule;}
struct qca_ppe_priv {struct list_head fw_pending,flow_list;int fw_pending_lock,flow_lock,vlan_lock;bool fw_flow_reserved;};
struct ppe_flow_block {struct qca_ppe_priv *priv;struct flow_block *block;};
struct ppe_flow_entry {struct list_head list;struct flow_block *block;unsigned long cookie;bool steer;};
static int backend_result,undo_count,install_count,fail_install_at;
static bool backend_owned=true;
static int ppe_fw_flow_offload(struct qca_ppe_priv *p,struct flow_cls_offload *c,const struct flow_block *b,bool *owned){
 (void)p;(void)b;*owned=backend_owned;if(c->command==FLOW_CLS_DESTROY){undo_count++;return 0;}return backend_result;
}
static bool ppe_flow_ethernet_pair(struct qca_ppe_priv *p,struct flow_cls_offload *c){(void)p;(void)c;return true;}
static int ppe_flow_offload_replace(struct ppe_flow_block *b,struct flow_cls_offload *c,bool steer){
 struct ppe_flow_entry *e;
 assert(steer);install_count++;if(fail_install_at==install_count)return -ENOSPC;
 e=calloc(1,sizeof(*e));e->block=b->block;e->cookie=c->cookie;e->steer=true;list_add_tail(&e->list,&b->priv->flow_list);return 0;
}
static void ppe_flow_free(struct qca_ppe_priv *p,struct ppe_flow_entry *e){(void)p;list_del(&e->list);free(e);}
static int ppe_flow_offload_destroy(struct qca_ppe_priv *p,struct flow_cls_offload *c){(void)p;(void)c;return -ENOENT;}
static int ppe_flow_offload_stats(struct qca_ppe_priv *p,struct flow_cls_offload *c){(void)p;(void)c;return 0;}
struct ppe_fw_pending {
	struct list_head list;
	struct flow_block *block;
	unsigned long flow;
	struct flow_cls_offload cls;
	struct nf_flow_rule saved;
};

static struct flow_offload *ppe_fw_connection(unsigned long cookie)
{
	const struct flow_offload_tuple *tuple = (const void *)cookie;
	struct flow_offload_tuple_rhash *th;

	th = container_of(tuple, struct flow_offload_tuple_rhash, tuple);
	return container_of(th - tuple->dir, struct flow_offload, tuplehash[0]);
}

static void ppe_fw_pending_free(struct ppe_fw_pending *pending)
{
	struct flow_action_entry *act;
	int i;

	flow_action_for_each(i, act, &pending->saved.rule->action)
		if (act->id == FLOW_ACTION_REDIRECT)
			dev_put(act->dev);
	list_del(&pending->list);
	kfree(pending->saved.rule);
	kfree(pending);
}

/* fw_pending_lock serializes offers, rollback and firmware-stop cleanup. */
static void ppe_fw_pending_drop(struct qca_ppe_priv *priv,
			       struct flow_block *block, unsigned long flow)
{
	struct ppe_fw_pending *pending, *tmp;

	list_for_each_entry_safe(pending, tmp, &priv->fw_pending, list)
		if ((!block || pending->block == block) &&
		    (!flow || pending->flow == flow))
			ppe_fw_pending_free(pending);
}

static int ppe_fw_pending_save(struct ppe_flow_block *fb,
			       struct flow_cls_offload *cls)
{
	struct flow_rule *rule = flow_cls_offload_flow_rule(cls);
	struct ppe_fw_pending *pending, *old, *tmp;
	struct flow_action_entry *act;
	int i;

	pending = kzalloc(sizeof(*pending), GFP_KERNEL);
	if (!pending)
		return -ENOMEM;
	pending->saved.rule = flow_rule_alloc(rule->action.num_entries);
	if (!pending->saved.rule) {
		kfree(pending);
		return -ENOMEM;
	}
	pending->saved.match.dissector = *rule->match.dissector;
	memcpy(&pending->saved.match.key, rule->match.key,
	       sizeof(pending->saved.match.key));
	memcpy(&pending->saved.match.mask, rule->match.mask,
	       sizeof(pending->saved.match.mask));
	pending->saved.rule->match.dissector = &pending->saved.match.dissector;
	pending->saved.rule->match.key = &pending->saved.match.key;
	pending->saved.rule->match.mask = &pending->saved.match.mask;
	memcpy(pending->saved.rule->action.entries, rule->action.entries,
	       sizeof(rule->action.entries[0]) * rule->action.num_entries);
	flow_action_for_each(i, act, &pending->saved.rule->action)
		if (act->id == FLOW_ACTION_REDIRECT)
			dev_hold(act->dev);
	pending->cls = *cls;
	pending->cls.common.extack = NULL;
	pending->cls.rule = pending->saved.rule;
	pending->block = fb->block;
	pending->flow = (unsigned long)ppe_fw_connection(cls->cookie);

	list_for_each_entry_safe(old, tmp, &fb->priv->fw_pending, list)
		if (old->block == fb->block && old->cls.cookie == cls->cookie)
			ppe_fw_pending_free(old);
	list_add_tail(&pending->list, &fb->priv->fw_pending);
	return 0;
}

static void ppe_fw_pair_rollback(struct ppe_flow_block *fb,
				 struct flow_cls_offload *cls)
{
	struct flow_offload *flow = ppe_fw_connection(cls->cookie);
	struct qca_ppe_priv *priv = fb->priv;
	struct ppe_flow_entry *entry, *tmp;
	unsigned long original = (unsigned long)&flow->tuplehash[0].tuple;
	unsigned long reply = (unsigned long)&flow->tuplehash[1].tuple;

	ppe_fw_pending_drop(priv, fb->block, (unsigned long)flow);
	guard(mutex)(&priv->flow_lock);
	guard(mutex)(&priv->vlan_lock);
	list_for_each_entry_safe(entry, tmp, &priv->flow_list, list)
		if (entry->block == fb->block && entry->steer &&
		    (entry->cookie == original || entry->cookie == reply))
			ppe_flow_free(priv, entry);
}

static int ppe_flow_block_cb(enum tc_setup_type type, void *type_data,
			     void *cb_priv)
{
	struct flow_cls_offload *cls = type_data;
	struct ppe_flow_block *fb = cb_priv;
	struct qca_ppe_priv *priv = fb->priv;
	struct ppe_fw_pending *pending;
	unsigned long flow;
	bool owned;
	int ret;

	if (type != TC_SETUP_CLSFLOWER)
		return -EOPNOTSUPP;

	guard(mutex)(&priv->fw_pending_lock);
	ret = ppe_fw_flow_offload(priv, cls, fb->block, &owned);
	if (!owned && READ_ONCE(priv->fw_flow_reserved) &&
	    cls->command == FLOW_CLS_REPLACE &&
	    ppe_flow_ethernet_pair(priv, cls)) {
		ppe_fw_pair_rollback(fb, cls);
		return -EOPNOTSUPP;
	}
	if (owned) {
		switch (cls->command) {
		case FLOW_CLS_REPLACE:
			if (ret && ret != -EAGAIN)
				goto rollback;
			/* No hardware entry is installed for a pending offer,
			 * and -EAGAIN prevents a false HW_OFFLOAD indication.
			 */
			{
				int save_ret = ppe_fw_pending_save(fb, cls);

				if (save_ret) {
					ret = save_ret;
					goto rollback;
				}
			}
			if (ret == -EAGAIN)
				return ret;

			flow = (unsigned long)ppe_fw_connection(cls->cookie);
			list_for_each_entry(pending, &priv->fw_pending, list) {
				if (pending->block != fb->block ||
				    pending->flow != flow)
					continue;
				ret = ppe_flow_offload_replace(fb, &pending->cls, true);
				if (ret)
					goto rollback;
			}
			ppe_fw_pending_drop(priv, fb->block, flow);
			return 0;
		case FLOW_CLS_DESTROY:
			ppe_fw_pair_rollback(fb, cls);
			return ret;
		case FLOW_CLS_STATS:
			return ret;
		default:
			return -EOPNOTSUPP;
		}
	}

	switch (cls->command) {
	case FLOW_CLS_REPLACE:
		return ppe_flow_offload_replace(fb, cls, false);
	case FLOW_CLS_DESTROY:
		ppe_fw_pending_drop(priv, fb->block,
				    (unsigned long)ppe_fw_connection(cls->cookie));
		return ppe_flow_offload_destroy(priv, cls);
	case FLOW_CLS_STATS:
		return ppe_flow_offload_stats(priv, cls);
	default:
		return -EOPNOTSUPP;
	}

rollback:
	/* Remove both PPE directions, then withdraw the shared NSS rule.
	 * This also handles the second PPE insertion failing after the first.
	 */
	ppe_fw_pair_rollback(fb, cls);
	{
		struct flow_cls_offload undo = *cls;

		undo.command = FLOW_CLS_DESTROY;
		ppe_fw_flow_offload(priv, &undo, fb->block, &owned);
	}
	return ret;
}


static int count(struct list_head *h){int n=0;struct list_head *p;for(p=h->next;p!=h;p=p->next)n++;return n;}
static void init(struct qca_ppe_priv *p){memset(p,0,sizeof(*p));INIT_LIST_HEAD(&p->fw_pending);INIT_LIST_HEAD(&p->flow_list);p->fw_flow_reserved=true;backend_owned=true;backend_result=-EAGAIN;undo_count=install_count=fail_install_at=fail_alloc=0;}
int main(void){
 struct qca_ppe_priv p;struct flow_block block={0};struct ppe_flow_block fb={&p,&block};
 struct flow_offload flow={.tuplehash={{{0}},{{1}}}};
 struct net_device dev={1};struct nf_flow_match match={0};
 struct flow_rule *rule=flow_rule_alloc(1);
 struct flow_cls_offload cls={.command=FLOW_CLS_REPLACE,.rule=rule};
 struct ppe_fw_pending *pending;
 rule->match=(struct flow_match){&match.dissector,&match.key,&match.mask};
 rule->action.entries[0]=(struct flow_action_entry){FLOW_ACTION_REDIRECT,&dev};
 match.key.value[0]=100;
 init(&p);cls.cookie=(unsigned long)&flow.tuplehash[0].tuple;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EAGAIN);
 assert(count(&p.fw_pending)==1&&count(&p.flow_list)==0&&dev.refs==2);
 pending=container_of(p.fw_pending.next,struct ppe_fw_pending,list);
 assert(pending->saved.rule->match.key!=rule->match.key);
 assert(pending->saved.rule->match.mask!=rule->match.mask);
 match.key.value[0]=200;assert(pending->saved.match.key.value[0]==100);
 cls.cookie=(unsigned long)&flow.tuplehash[1].tuple;backend_result=-EIO;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EIO);
 assert(!count(&p.fw_pending)&&!count(&p.flow_list)&&dev.refs==1&&undo_count==1);
 puts("PASS: no early steering; copied rule lifetime; second-direction rejection rollback");

 init(&p);cls.cookie=(unsigned long)&flow.tuplehash[0].tuple;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EAGAIN);
 cls.cookie=(unsigned long)&flow.tuplehash[1].tuple;backend_result=0;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==0);
 assert(!count(&p.fw_pending)&&count(&p.flow_list)==2&&dev.refs==1);
 cls.command=FLOW_CLS_DESTROY;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==0);
 assert(!count(&p.flow_list));
 puts("PASS: pair commit installs both directions; destroy clears both");

 init(&p);cls.command=FLOW_CLS_REPLACE;cls.cookie=(unsigned long)&flow.tuplehash[0].tuple;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EAGAIN);
 cls.cookie=(unsigned long)&flow.tuplehash[1].tuple;backend_result=0;fail_install_at=2;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-ENOSPC);
 assert(!count(&p.fw_pending)&&!count(&p.flow_list)&&undo_count==1&&dev.refs==1);
 puts("PASS: second PPE insertion failure rolls back first entry and NSS rule");

 init(&p);cls.cookie=(unsigned long)&flow.tuplehash[0].tuple;fail_alloc=1;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-ENOMEM);
 assert(!count(&p.fw_pending)&&!count(&p.flow_list)&&undo_count==1&&dev.refs==1);
 puts("PASS: allocation failure withdraws pending NSS state");

 init(&p);assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EAGAIN);
 backend_owned=false;cls.cookie=(unsigned long)&flow.tuplehash[1].tuple;
 assert(ppe_flow_block_cb(TC_SETUP_CLSFLOWER,&cls,&fb)==-EOPNOTSUPP);
 assert(!count(&p.fw_pending)&&!count(&p.flow_list)&&dev.refs==1);
 puts("PASS: unavailable backend clears pending pair and preserves software fallback");
 free(rule);return 0;
}
