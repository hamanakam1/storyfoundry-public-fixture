#!/usr/bin/env python3
"""Deterministic, target-independent synthetic business history. No network or import."""
from __future__ import annotations
import argparse, calendar, collections, csv, datetime as dt, hashlib, html, json, random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NOTICE='SYNTHETIC FICTION — NOT REAL PEOPLE, CUSTOMERS, TRANSACTIONS OR BUSINESS EVIDENCE'
LINKS={
 'customers':{'account_id':'accounts','lead_id':'leads'},
 'contacts':{'account_id':'accounts'},'leads':{'account_id':'accounts','contact_id':'contacts','owner_id':'staff','campaign_id':'campaigns'},
 'opportunities':{'lead_id':'leads','account_id':'accounts','owner_id':'staff'},
 'staff':{'talent_id':'talent'},'talent_skills':{'talent_id':'talent','skill_id':'skills'},
 'campaign_memberships':{'campaign_id':'campaigns','lead_id':'leads'},
 'contracts':{'customer_id':'customers','project_id':'projects','service_id':'services'},
 'contract_lines':{'contract_id':'contracts'},'projects':{'customer_id':'customers','contract_id':'contracts','manager_id':'staff'},
 'talent_assignments':{'project_id':'projects','staff_id':'staff'},
 'milestones':{'project_id':'projects'},'tasks':{'project_id':'projects','milestone_id':'milestones','owner_id':'staff'},
 'task_dependencies':{'task_id':'tasks','depends_on_task_id':'tasks'},
 'time_entries':{'project_id':'projects','task_id':'tasks','staff_id':'staff'},
 'expenses':{'project_id':'projects','staff_id':'staff'},
 'billing_schedule':{'contract_id':'contracts'},'invoices':{'contract_id':'contracts','customer_id':'customers','billing_schedule_id':'billing_schedule'},
 'invoice_lines':{'invoice_id':'invoices'},'credit_notes':{'invoice_id':'invoices'},
 'payments':{'invoice_id':'invoices','customer_id':'customers'},'payment_attempts':{'invoice_id':'invoices'},
 'support_tickets':{'customer_id':'customers','project_id':'projects','owner_id':'staff'},
 'meetings':{'account_id':'accounts','contact_id':'contacts','organizer_id':'staff'},
 'meeting_attendees':{'meeting_id':'meetings','contact_id':'contacts','staff_id':'staff'},
 'conversations':{'lead_id':'leads','contact_id':'contacts','owner_id':'staff'},
 'messages':{'conversation_id':'conversations','contact_id':'contacts','staff_id':'staff'},
 'knowledge_versions':{'knowledge_id':'knowledge','author_id':'staff'},
 'notes':{'author_id':'staff'},'activities':{'actor_id':'staff'},'story_events':{},
}
FIRST_A=['Ava','Bela','Ceri','Dara','Eli','Fara','Gala','Heri','Ila','Jora','Kala','Liri','Mara','Neri','Ori','Pera','Quera','Rina','Sora','Tali']
FIRST_B=['ven','lune','rin','sol','mere']
LAST_A=['Amber','Birch','Cloud','Dawn','Elm','Fern','Glen','Harbor','Ivory','Juniper','Kestrel','Lumen','Maple','North','Opal','Pine','Quartz','River','Silver','Thistle']
LAST_B=['crest','field','haven','ridge','vale']
def person_name(index, cohort='talent'):
    # Separate fictional naming namespaces for contacts and talent; no source names.
    first=FIRST_A[(index//5)%20]+FIRST_B[index%5]
    last=LAST_A[(index//500)%20]+LAST_B[(index//100)%5]
    return f'{first} {last}' + ('' if cohort=='talent' else f' {cohort.title()}')
def stamp(day,hour=12):return day.isoformat()+f'T{hour:02d}:00:00Z'
def dumps(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(x):return hashlib.sha256(dumps(x).encode()).hexdigest()
def csv_value(x):
    if x is None:return ''
    if isinstance(x,(list,dict)):x=dumps(x)
    elif isinstance(x,bool):x='true' if x else 'false'
    else:x=str(x)
    # Spreadsheet-safe transport; importer must remove this documented escape only on text.
    return "'"+x if x.startswith(('=','+','-','@','\t','\r')) else x

def build(config, shapes):
    if config.get('synthetic') is not True:raise ValueError('Synthetic configuration required')
    if config['customers']>config['leads']:raise ValueError('Customers cannot exceed leads')
    rng=random.Random(config['seed']); start=dt.date.fromisoformat(config['history_start']); anchor=dt.date.fromisoformat(config['anchor_date'])
    span=(anchor-start).days
    if span<180:raise ValueError('At least 180 days required for this scenario')
    count=config['customers'];lead_count=config['leads'];talent_count=config['talent']
    all_shapes=[x for shape in shapes['shapes'] for x in [shape]*shape['count']]
    if len(all_shapes)!=talent_count:raise ValueError('Profile-shape counts must exactly match configured talent')
    dataset_id='synthetic-'+digest({'config':config,'shapes':shapes['shapes']})[:12]
    tables=collections.defaultdict(list)
    def ident(domain,n):return f'{dataset_id[10:]}-{domain}-{n:06d}'
    def add(domain,**kw):
        row={'id':ident(domain,len(tables[domain])+1),'dataset_id':dataset_id,'synthetic':True,**kw}
        tables[domain].append(row);return row
    def day(offset):return start+dt.timedelta(days=max(0,min(span,offset)))
    def relative(origin,offset):return min(anchor,origin+dt.timedelta(days=offset))
    def staff_id(n):return ident('staff',n%config['staff']+1)
    def note(domain,record,text,when,n=0):return add('notes',subject_domain=domain,subject_id=record['id'],author_id=staff_id(n),created_at=stamp(when),body='[SYNTHETIC] '+text)
    def activity(domain,record,kind,when,n=0):return add('activities',subject_domain=domain,subject_id=record['id'],actor_id=staff_id(n),occurred_at=stamp(when),kind=kind,summary='[SYNTHETIC] '+kind.replace('_',' '),delivery='SIMULATED_ONLY')
    add('company',name=config['company_name'],expanded_name=config['company_expansion'],scenario=config['scenario'],founded_on=start.isoformat(),website='https://company.example.invalid',currency=config['currency'],notice=NOTICE,talent_interpretation=f'Fictional expert network, not {talent_count:,} employees; only staff records are engaged by the fictional company')
    skills=sorted({s for shape in all_shapes for s in shape['skills']});skill_ids={}
    for s in skills:skill_ids[s]=add('skills',name=s,classification='FICTIONAL_PROFILE_CAPABILITY')['id']
    for i,shape in enumerate(all_shapes):
        p=add('talent',display_name=person_name(i),title=shape['title'],email=f'talent{i+1:05d}@people.example.invalid',phone=None,location='Fictional City, Exampleland',pool_status='FICTIONAL_NETWORK',bio=f"[SYNTHETIC] Imaginary {shape['title'].lower()} practicing {', '.join(shape['skills'][:3])}. No real employment, credentials or biography claimed.",available_from=start.isoformat())
        for skill in sorted(set(shape['skills'])):add('talent_skills',talent_id=p['id'],skill_id=skill_ids[skill],level=1+(i+skills.index(skill))%5,evidence_type='SYNTHETIC_SCENARIO_ASSIGNMENT')
    for i in range(config['staff']):
        talent=tables['talent'][round(i*(talent_count-1)/max(1,config['staff']-1))]
        add('staff',talent_id=talent['id'],display_name=talent['display_name'],title=talent['title'],engagement='FICTIONAL_EMPLOYEE' if i<32 else 'FICTIONAL_CONTRACTOR',joined_on=start.isoformat(),hourly_cost_cents=4500+500*(i%9),currency=config['currency'])
    service_specs=config.get('services') or [('Readiness assessment',1500000),('Commercial and listing preparation',2400000),('Fulfillment design review',3600000),('Usage accounting rehearsal',4500000),('Customer onboarding enablement',2800000),('Managed evidence review',1800000)]
    if len(service_specs)!=6:raise ValueError('This story template requires six service offerings')
    for title,price in service_specs:add('services',name=title,base_fee_cents=price,currency=config['currency'],promise='FICTIONAL consulting deliverable; no external approval, accreditation or partnership claimed')
    for i in range(24):
        cstart=day(round(i*span/24));cend=day(round((i+1)*span/24)-1)
        add('campaigns',name=f'[SYNTHETIC] Cohort {i+1:02d} — '+['Readiness clinic','Operator workshop','Evidence playbook','Referral roundtable'][i%4],channel=['fictional_email','fictional_webinar','fictional_referral','fictional_content'][i%4],starts_on=cstart.isoformat(),ends_on=cend.isoformat(),budget_cents=50000+i*2500,status='SIMULATED_CLOSED',sent_real_messages=False)
    customer_dates={}; lead_dates={}
    stage_counts=collections.Counter()
    for i in range(lead_count):
        won=i<count
        if won:
            closed=day(14+round(((i+1)/count)**0.82*(span-75)))
            created=max(start,closed-dt.timedelta(days=7+i%13));customer_dates[i]=closed
            stage='won'
        else:
            j=i-count; ratio=j/max(1,lead_count-count)
            stage='lost' if ratio<.35 else 'nurturing' if ratio<.55 else 'qualified' if ratio<.70 else 'contacted' if ratio<.825 else 'new'
            # Seasonally weighted deterministic acquisition; weak summer and stronger Q4.
            while True:
                created=day(rng.randrange(max(1,span-25 if stage=='lost' else span+1)))
                weight=.52 if created.month in (7,8) else 1.0 if created.month in (10,11,12) else .78
                if rng.random()<weight:break
            closed=relative(created,8+i%20) if stage=='lost' else None
        lead_dates[i]=created;stage_counts[stage]+=1
        company=f'[SYNTHETIC] {LAST_A[i%20]} { ["Systems","Analytics","Workflow","Signals","Platform"][i//20%5]} {i+1:03d}'
        account=add('accounts',name=company,account_type='customer' if won else 'prospect',industry=['Developer tools','Business software','Data operations','Security software','Industry applications'][i%5],website=f'https://vendor{i+1:04d}.example.invalid',email=f'hello@vendor{i+1:04d}.example.invalid',phone=f'+1-202-555-01{i%100:02d}',address=f'{i+1} Simulation Lane, Fictional City, ZZ 00000, Exampleland',created_at=stamp(created))
        contact=add('contacts',account_id=account['id'],display_name=person_name(i,'contact'),first_name=person_name(i,'contact').split()[0],last_name=' '.join(person_name(i,'contact').split()[1:]),email=f'contact{i+1:04d}@vendor{i+1:04d}.example.invalid',phone=None,title=['Founder','Operations lead','Product lead','Commercial lead'][i%4],created_at=stamp(created),consent='SIMULATED_NO_CONTACT_PERMISSION')
        campaign=ident('campaigns',min(24,1+int((created-start).days*24/(span+1))))
        lead=add('leads',account_id=account['id'],contact_id=contact['id'],owner_id=staff_id(i),campaign_id=campaign,status=stage,created_at=stamp(created),closed_at=stamp(closed) if closed else None,loss_reason=['budget deferred','fit outside scope','in-house alternative','timing not ready'][i%4] if stage=='lost' else None,score=30+(i*17)%71,source='SYNTHETIC_'+['referral','workshop','inbound','outbound'][i%4])
        add('campaign_memberships',campaign_id=campaign,lead_id=lead['id'],joined_at=stamp(created),status='SIMULATED_ENGAGED')
        add('opportunities',lead_id=lead['id'],account_id=account['id'],owner_id=staff_id(i),name=f'[SYNTHETIC] Vendor {i+1:03d} readiness engagement',stage='closed_won' if won else 'closed_lost' if stage=='lost' else stage,amount_cents=service_specs[i%6][1],currency=config['currency'],created_at=stamp(created),closed_on=closed.isoformat() if closed else None,expected_close_on=(closed or anchor+dt.timedelta(days=14+i%60)).isoformat())
        conv=add('conversations',lead_id=lead['id'],contact_id=contact['id'],owner_id=staff_id(i),subject='[SYNTHETIC] Scope and evidence discussion',channel='FICTIONAL_EMAIL_THREAD',created_at=stamp(created))
        for j in range(3):
            add('messages',conversation_id=conv['id'],contact_id=contact['id'] if j%2==0 else None,staff_id=staff_id(i) if j%2 else None,occurred_at=stamp(relative(created,j*2),10+j),direction='simulated_inbound' if j%2==0 else 'simulated_outbound',body='[SYNTHETIC] '+['Please explain the bounded readiness review and owner responsibilities.','We propose an evidence review with explicit exclusions, milestones and acceptance.','The fictional team will review scope, budget and timing before a decision.'][j],delivery_state='NOT_SENT_SIMULATION')
        note('leads',lead,f'Fictional acquisition cohort; recorded stage {stage}. No real outreach or customer relationship exists.',created,i)
        activity('leads',lead,'lead_recorded',created,i)
        if won:
            cust=add('customers',account_id=account['id'],lead_id=lead['id'],name=company,converted_on=closed.isoformat(),status='FICTIONAL_PAYING_CUSTOMER',segment=['starter','growth','scale'][i%3],real_customer=False)
            add('contacts',account_id=account['id'],display_name=person_name(i,'finance'),first_name=person_name(i,'finance').split()[0],last_name=' '.join(person_name(i,'finance').split()[1:]),email=f'finance@vendor{i+1:04d}.example.invalid',phone=None,title='Fictional finance contact',created_at=stamp(closed),consent='SIMULATED_NO_CONTACT_PERMISSION')
            activity('customers',cust,'fictional_sale_won',closed,i)
    # One primary project per customer; repeat engagements for the oldest 40 percent.
    project_number=0
    for i,cust in enumerate(tables['customers']):
        for repeat in range(2 if i<int(count*.4) else 1):
            signed=customer_dates[i]+dt.timedelta(days=180*repeat)
            if signed>anchor:continue
            project_number+=1;service=tables['services'][(i+repeat)%6]
            total=service['base_fee_cents']+(i%4)*100000
            expected_end=signed+dt.timedelta(days=90)
            completed=expected_end<=anchor
            contract_id=ident('contracts',project_number);project_id=ident('projects',project_number)
            contract=add('contracts',customer_id=cust['id'],project_id=project_id,service_id=service['id'],title=f'[SYNTHETIC] Engagement {project_number:03d}',signed_on=signed.isoformat(),starts_on=signed.isoformat(),ends_on=expected_end.isoformat(),amount_cents=total,currency=config['currency'],status='completed' if completed else 'active',document_notice=NOTICE)
            for desc,amount in [('Consulting scope',total*4//5),('Workshop and handoff',total-total*4//5)]:add('contract_lines',contract_id=contract_id,description='[SYNTHETIC] '+desc,quantity=1,unit_price_cents=amount,line_total_cents=amount)
            project=add('projects',customer_id=cust['id'],contract_id=contract_id,manager_id=staff_id(i),name=f'[SYNTHETIC] {service["name"]} — {project_number:03d}',starts_on=signed.isoformat(),target_ends_on=expected_end.isoformat(),completed_on=expected_end.isoformat() if completed else None,status='completed' if completed else 'active',outcome='FICTIONAL deliverable accepted; no external approval claim' if completed else 'Fictional delivery in progress',budget_cents=total)
            for j in range(3):add('talent_assignments',project_id=project_id,staff_id=staff_id(i+j*7),role=['delivery lead','reviewer','specialist'][j],starts_on=signed.isoformat(),ends_on=expected_end.isoformat(),allocation_percent=10+j*5)
            milestones=[]
            for j,name in enumerate(['Scope agreed','Evidence mapped','Draft reviewed','Rework resolved','Handoff accepted']):
                due=signed+dt.timedelta(days=j*20+5)
                milestones.append(add('milestones',project_id=project_id,name='[SYNTHETIC] '+name,due_on=due.isoformat(),completed_on=due.isoformat() if due<=anchor else None,status='completed' if due<=anchor else 'planned'))
            task_rows=[]
            for j in range(10):
                due=signed+dt.timedelta(days=j*9+2);done=due<=anchor-dt.timedelta(days=3)
                task=add('tasks',project_id=project_id,milestone_id=milestones[j//2]['id'],owner_id=staff_id(i+j),title='[SYNTHETIC] '+['Confirm scope exclusions','Map owner decisions','Inventory evidence','Review applicability','Draft findings','Review correction','Reconcile references','Prepare handoff','Rehearse operator review','Accept bounded outcome'][j],created_at=stamp(signed),due_on=due.isoformat(),completed_at=stamp(due) if done else None,status='completed' if done else 'planned',priority='high' if j in (0,5,9) else 'normal')
                task_rows.append(task)
                if j:add('task_dependencies',task_id=task['id'],depends_on_task_id=task_rows[j-1]['id'],kind='finish_to_start')
            for j in range(20):
                worked=signed+dt.timedelta(days=2+j*2)
                if worked>anchor:continue
                mins=60+30*((i+j)%5)
                add('time_entries',project_id=project_id,task_id=task_rows[min(9,j//2)]['id'],staff_id=staff_id(i+j%3),worked_on=worked.isoformat(),minutes=mins,billable=True,description='[SYNTHETIC] Evidence review and delivery work',approval='SIMULATED_APPROVED')
            for j in range(2):
                spent=relative(signed,10+j*20)
                add('expenses',project_id=project_id,staff_id=staff_id(i+j),spent_on=spent.isoformat(),category=['fictional_workshop_supplies','fictional_training'][j],amount_cents=2500+(i%7)*500,currency=config['currency'],status='SIMULATED_APPROVED',receipt_reference='synthetic-receipt-'+str(project_number)+'-'+str(j))
            for j,(offset,percent) in enumerate([(0,50),(30,30),(75,20)]):
                issue=signed+dt.timedelta(days=offset);gross=total*percent//100
                schedule=add('billing_schedule',contract_id=contract_id,scheduled_on=issue.isoformat(),amount_cents=gross,status='invoiced' if issue<=anchor else 'planned')
                if issue>anchor:continue
                due=issue+dt.timedelta(days=30)
                invoice=add('invoices',contract_id=contract_id,customer_id=cust['id'],billing_schedule_id=schedule['id'],invoice_number=f'SYN-{project_number:04d}-{j+1}',issued_on=issue.isoformat(),due_on=due.isoformat(),subtotal_cents=gross,tax_cents=0,total_cents=gross,currency=config['currency'],notice=NOTICE)
                for desc,amount in [('Consulting services',gross*4//5),('Workshop/handoff',gross-gross*4//5)]:add('invoice_lines',invoice_id=invoice['id'],description='[SYNTHETIC] '+desc,quantity=1,unit_price_cents=amount,line_total_cents=amount)
                credit=gross//20 if i%23==0 and j==2 else 0
                if credit:add('credit_notes',invoice_id=invoice['id'],issued_on=relative(issue,2).isoformat(),amount_cents=credit,reason='[SYNTHETIC] Agreed scope reduction',status='posted')
                payment_day=issue+dt.timedelta(days=7 if j==0 else 20+i%15)
                available=gross-credit;paid=available if payment_day<=anchor else 0
                if j>0 and i%11==0:paid=available//2 if payment_day<=anchor else 0
                if paid:
                    add('payments',invoice_id=invoice['id'],customer_id=cust['id'],paid_on=payment_day.isoformat(),amount_cents=paid,currency=config['currency'],method='FICTIONAL_BANK_TRANSFER',external_reference=f'SIMULATED-PAY-{project_number}-{j}',status='posted')
                if i%19==0 and j==1:
                    add('payment_attempts',invoice_id=invoice['id'],attempted_on=relative(issue,4).isoformat(),amount_cents=available,status='SIMULATED_FAILED',reason='Fictional remittance reference mismatch; no real payment attempted')
                balance=available-paid
                invoice.update(credit_cents=credit,paid_cents=paid,balance_cents=balance,status='paid' if balance==0 else 'overdue' if due<anchor else 'partially_paid' if paid else 'issued')
                activity('invoices',invoice,'invoice_simulated',issue,i)
            note('projects',project,'Fictional project history: scope clarified, evidence reviewed and handoff recorded. Output acceptance is not external approval.',signed,i)
            activity('projects',project,'project_recorded',signed,i)
            if repeat==0:
                for j in range(3):
                    opened=relative(signed,10+j*25);resolved=opened+dt.timedelta(days=2+i%8)
                    add('support_tickets',customer_id=cust['id'],project_id=project_id,owner_id=staff_id(i+j),subject='[SYNTHETIC] '+['Scope interpretation','Evidence freshness','Handoff clarification'][j],opened_at=stamp(opened),resolved_at=stamp(resolved) if resolved<=anchor else None,status='resolved' if resolved<=anchor else 'open',priority='high' if i%10==0 else 'normal',resolution='[SYNTHETIC] Clarified owner and updated fictional review notes' if resolved<=anchor else None)
    for i,cust in enumerate(tables['customers']):
        for j in range(4):
            when=relative(customer_dates[i],1+j*14)
            meeting=add('meetings',account_id=cust['account_id'],contact_id=ident('contacts',i*2+1),organizer_id=staff_id(i),title='[SYNTHETIC] '+['Kickoff','Evidence review','Correction review','Handoff planning'][j],starts_at=stamp(when,15),ends_at=stamp(when,16),status='cancelled' if i%17==0 and j==1 else 'completed',location='https://meeting.example.invalid/room/'+str(i+1),notifications_sent=False)
            # Customer primary contacts are not contiguous after noncustomer generation; fix by account.
            meeting['contact_id']=next(c['id'] for c in tables['contacts'] if c['account_id']==cust['account_id'])
            add('meeting_attendees',meeting_id=meeting['id'],contact_id=meeting['contact_id'],staff_id=None,response='SIMULATED_ACCEPTED')
            add('meeting_attendees',meeting_id=meeting['id'],contact_id=None,staff_id=staff_id(i),response='SIMULATED_ACCEPTED')
    for i in range(config['future_meetings']):
        cust=tables['customers'][i%count];when=anchor+dt.timedelta(days=1+i%45)
        contact=next(c for c in tables['contacts'] if c['account_id']==cust['account_id'])
        meeting=add('meetings',account_id=cust['account_id'],contact_id=contact['id'],organizer_id=staff_id(i),title='[SYNTHETIC FUTURE] Quarterly planning',starts_at=stamp(when,15),ends_at=stamp(when,16),status='scheduled',location='https://meeting.example.invalid/future/'+str(i+1),notifications_sent=False)
        add('meeting_attendees',meeting_id=meeting['id'],contact_id=contact['id'],staff_id=None,response='SIMULATED_TENTATIVE')
        add('meeting_attendees',meeting_id=meeting['id'],contact_id=None,staff_id=staff_id(i),response='SIMULATED_TENTATIVE')
    for i in range(60):
        created=day(i*span//60)
        doc=add('knowledge',title='[SYNTHETIC] '+['Scope-first consulting','Evidence and owner review','Payment reconciliation','Handoff continuity','Fictional workshop facilitation','Customer question triage'][i%6]+f' {i+1:02d}',created_at=stamp(created),owner_id=staff_id(i),status='FICTIONAL_INTERNAL_GUIDE',body='[SYNTHETIC] Original scenario guidance: record scope, distinguish evidence from proposals, assign an owner, review corrections, and confirm a bounded outcome. This is not current provider policy or certification guidance.')
        for rev in range(1,3):add('knowledge_versions',knowledge_id=doc['id'],author_id=staff_id(i),version=rev,recorded_at=stamp(relative(created,(rev-1)*7)),change_note='[SYNTHETIC] '+('Initial original guide' if rev==1 else 'Clarified responsibilities after a fictional support question'))
    for title,when,reason in [('Founding and first playbook',start,'company'),('Summer pipeline softness',dt.date(anchor.year-1,7,15),'campaigns'),('Review discipline after scope losses',dt.date(anchor.year-1,10,15),'leads'),('Growing fictional customer cohort',dt.date(anchor.year,4,15),'customers'),('Current evidence cut',anchor,'company')]:
        if start<=when<=anchor:add('story_events',title='[SYNTHETIC] '+title,occurred_on=when.isoformat(),supporting_domain=reason,interpretation='Authored simulation arc, supported by generated cohort and outcome records; never a real business event')
    LINKS['knowledge']={'owner_id':'staff'}
    return dict(tables),{'dataset_id':dataset_id,'config':config,'profile_provenance':shapes.get('provenance',{}),'profile_shape_sha256':digest(shapes),'title_counts':dict(collections.Counter(p['title'] for p in tables['talent'])),'skill_incidence_counts':dict(collections.Counter(skills[[x['id'] for x in tables['skills']].index(link['skill_id'])] for link in tables['talent_skills']))}

def summary(tables,meta):
    months=collections.defaultdict(lambda:dict(leads=0,customers=0,cash_collected_cents=0,invoiced_cents=0,worked_minutes=0))
    for r in tables['leads']:months[r['created_at'][:7]]['leads']+=1
    for r in tables['customers']:months[r['converted_on'][:7]]['customers']+=1
    for r in tables['payments']:months[r['paid_on'][:7]]['cash_collected_cents']+=r['amount_cents']
    for r in tables['invoices']:months[r['issued_on'][:7]]['invoiced_cents']+=r['total_cents']
    for r in tables['time_entries']:months[r['worked_on'][:7]]['worked_minutes']+=r['minutes']
    return {'synthetic':True,'notice':NOTICE,'dataset_id':meta['dataset_id'],'history_start':meta['config']['history_start'],'anchor_date':meta['config']['anchor_date'],'counts':{k:len(v) for k,v in sorted(tables.items())},'lead_stages':dict(collections.Counter(r['status'] for r in tables['leads'])),'project_states':dict(collections.Counter(r['status'] for r in tables['projects'])),'financials':{'currency':meta['config']['currency'],'contracted_cents':sum(r['amount_cents'] for r in tables['contracts']),'invoiced_cents':sum(r['total_cents'] for r in tables['invoices']),'credits_cents':sum(r['amount_cents'] for r in tables.get('credit_notes',[])),'cash_collected_cents':sum(r['amount_cents'] for r in tables['payments']),'outstanding_cents':sum(r['balance_cents'] for r in tables['invoices']),'basis':'Synthetic operational arithmetic, not GAAP revenue or a real company performance claim'},'future_meetings':sum(r['status']=='scheduled' for r in tables['meetings']),'monthly_cohorts':[{'month':m,**v} for m,v in sorted(months.items())]}

def chart(rows,key,title,path):
    # Standalone accessible SVG chart; deterministic artifact with a data table beside it.
    vals=[r[key] for r in rows];maximum=max(vals or [1]) or 1;w=1100;h=390;left=65;bottom=320;top=75;barw=900/max(1,len(rows))
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)} — synthetic data"><rect width="100%" height="100%" fill="#f8fafc"/><text x="30" y="30" font-family="sans-serif" font-size="19">{html.escape(title)}</text><text x="30" y="53" font-family="sans-serif" font-size="12">SYNTHETIC FICTION — NOT REAL BUSINESS RESULTS</text>']
    for i,(r,v) in enumerate(zip(rows,vals)):
        height=(bottom-top)*v/maximum;x=left+i*barw
        out.append(f'<rect x="{x:.2f}" y="{bottom-height:.2f}" width="{barw-5:.2f}" height="{height:.2f}" fill="#2563eb"><title>{r["month"]}: {v}</title></rect><text transform="translate({x+4:.2f},{bottom+15}) rotate(45)" font-family="sans-serif" font-size="10">{r["month"]}</text>')
    out.append(f'<text x="15" y="{top+5}" font-family="sans-serif" font-size="11">{maximum:,}</text><text x="35" y="{bottom}" font-family="sans-serif" font-size="11">0</text></svg>')
    path.write_text(''.join(out))

def write_dataset(tables,meta,out,narrative=''):
    out=Path(out)
    if out.exists() and any(out.iterdir()) and not (out/'manifest.json').exists():
        raise ValueError('Refusing to overwrite a nonempty unowned directory')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():
        old=json.loads((out/'manifest.json').read_text())
        if old.get('generator')!='synthetic-business-history':raise ValueError('Refusing to overwrite an unowned data directory')
    for sub in ['json','csv','charts']: (out/sub).mkdir(exist_ok=True)
    for domain,rows in sorted(tables.items()):
        (out/'json'/f'{domain}.jsonl').write_text(''.join(dumps(r)+'\n' for r in rows))
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (out/'csv'/f'{domain}.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            writer.writerows({k:csv_value(v) for k,v in r.items()} for r in rows)
    sm=summary(tables,meta);(out/'summary.json').write_text(json.dumps(sm,indent=2)+'\n')
    (out/'profile-provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    (out/'relationships.json').write_text(json.dumps(LINKS,indent=2)+'\n')
    with (out/'charts'/'monthly-cohorts.csv').open('w',newline='') as f:
        rows=sm['monthly_cohorts'];w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    chart(sm['monthly_cohorts'],'customers','Fictional customer acquisition by calendar month',out/'charts'/'customer-cohorts.svg')
    chart(sm['monthly_cohorts'],'cash_collected_cents','Fictional cash collections by month (USD cents)',out/'charts'/'cash-collections.svg')
    money=lambda cents:f'${cents/100:,.2f}'
    story=f'''# {meta['config']['company_name']} — fictional story bible

{NOTICE}

**{meta['config']['company_expansion']}** is an invented service business. History: {sm['history_start']} through {sm['anchor_date']}. All dates, names, relationships and outcomes are authored simulation. The {sm['counts']['talent']:,}-person talent pool is a fictional expert network; the {sm['counts']['staff']} staff records are its fictional engaged team. No source person's identity or biography is reused.

## Story supported by the dataset

The company begins with a scope-first review practice, records {sm['counts']['leads']} invented leads and completes {sm['counts']['customers']} fictional sales. Every customer has a posted synthetic payment. Lead outcomes are {json.dumps(sm['lead_stages'],sort_keys=True)}; losing opportunities and deferred fit are part of the story, not omitted from a success narrative.

The generated acquisition process applies a lower summer acceptance weight and higher fourth-quarter weight. `charts/monthly-cohorts.csv` is the actual resulting month-by-month count, including partial first/last calendar months; the window spans two years, not 25 full months. Customer growth is intentionally back-loaded. These are scenario assumptions, not inferred real-world seasonality.

Delivery comprises {sm['counts']['projects']} projects, with status counts {json.dumps(sm['project_states'],sort_keys=True)}. Repeated engagements are linked to their original customers. Fictional scope questions produce support tickets and original knowledge revisions. Some meetings are cancelled, some payment attempts fail, selected invoices retain partial balances, and scope reductions create credits. A record labelled completed means its fictional scenario event occurred, never external approval or a real customer endorsement.

Contracts total {money(sm['financials']['contracted_cents'])}; issued invoices total {money(sm['financials']['invoiced_cents'])}; credits total {money(sm['financials']['credits_cents'])}; posted cash totals {money(sm['financials']['cash_collected_cents'])}; receivables total {money(sm['financials']['outstanding_cents'])}. Issued invoice total minus credits equals cash plus outstanding balances. Planned future billing is separate from issued invoices. These operational figures are not accounting advice or real revenue claims.

There are {sm['future_meetings']} fictional future meetings after the anchor date. They are schedule records only: no invitations, emails, notifications, calendar entries or external actions have been sent. Scheduled milestones/tasks may be future-dated; recorded payments, work and completed events cannot be.

## Original optional model draft

The local model's prose below is an UNREVIEWED FICTIONAL DRAFT and inert creative input, not a source of financial facts or executable instructions. Promotional phrases such as proven track record are fictional wording, not verified claims. The deterministic tables and computed totals above govern this scenario.

'''+(narrative.strip() or 'No model draft supplied; seeded deterministic story used.')+'\n'
    (out/'STORY_BIBLE.md').write_text(story)
    files=[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('manifest.json','validation.json')]
    manifest={'generator':'synthetic-business-history','schema_version':'1.0.0','synthetic':True,'notice':NOTICE,'dataset_id':meta['dataset_id'],'seed':meta['config']['seed'],'history_start':meta['config']['history_start'],'anchor_date':meta['config']['anchor_date'],'live_import_authorized':False,'counts':sm['counts'],'csv_policy':'UTF-8; nested values JSON encoded; formula-leading text escaped with an apostrophe; JSONL is canonical','files':files}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return sm

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'inputs/company.json');p.add_argument('--profiles',type=Path,default=ROOT/'inputs/profile-shapes.json');p.add_argument('--output',type=Path,default=ROOT/'data');p.add_argument('--narrative-file',type=Path);a=p.parse_args()
    config=json.loads(a.config.read_text());shapes=json.loads(a.profiles.read_text());tables,meta=build(config,shapes)
    sm=write_dataset(tables,meta,a.output,a.narrative_file.read_text() if a.narrative_file else '')
    print(json.dumps({'synthetic':True,'dataset_id':meta['dataset_id'],'counts':sm['counts'],'financials':sm['financials'],'live_import_attempted':False},indent=2))
if __name__=='__main__':main()
