#!/usr/bin/env python3
"""Read-only deterministic dataset validation; no target-system operations."""
import argparse, collections, csv, datetime as dt, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit
from generate import LINKS, csv_value

PLANNING_DATE_FIELDS = {
    'expected_close_on', 'ends_on', 'target_ends_on', 'due_on', 'scheduled_on',
    'starts_at', 'ends_at',
}

def reserved_endpoint(field,value):
    if field=='phone':return value is None or isinstance(value,str) and re.fullmatch(r'\+1-202-555-01\d{2}',value) is not None
    if field=='email':
        if not isinstance(value,str) or value.count('@')!=1 or any(c.isspace() for c in value):return False
        local,domain=value.rsplit('@',1)
        return bool(local) and domain.endswith('.example.invalid')
    if field=='website':
        if not isinstance(value,str):return False
        try:url=urlsplit(value)
        except ValueError:return False
        return url.scheme=='https' and url.hostname is not None and url.hostname.endswith('.example.invalid') and url.username is None and url.password is None
    return True

def validate_tables(tables,config):
    errors=[];anchor=dt.date.fromisoformat(config['anchor_date']);start=dt.date.fromisoformat(config['history_start'])
    def check(ok,message):
        if not ok:errors.append(message)
    for domain,rows in tables.items():
        if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows):
            return [f'{domain}: malformed record or missing stable ID']
    index={domain:{r['id']:r for r in rows} for domain,rows in tables.items()}
    allids=[r['id'] for rows in tables.values() for r in rows]
    check(len(set(allids))==len(allids),'duplicate stable external IDs')
    for domain,rows in tables.items():
        for r in rows:
            check(r.get('synthetic') is True,f'{domain}/{r["id"]}: missing synthetic marker')
            for field,target in LINKS.get(domain,{}).items():
                value=r.get(field)
                if value is not None:check(value in index.get(target,{}),f'{domain}/{r["id"]}: dangling {field}')
            if 'subject_id' in r:check(r['subject_id'] in index.get(r['subject_domain'],{}),f'{domain}: dangling polymorphic subject')
            for k,v in r.items():
                if k.endswith('_cents'):check(type(v) is int and v>=0,f'{domain}: invalid monetary integer {k}')
                if k in ('email','website','phone') and not reserved_endpoint(k,v):check(False,f'{domain}: non-reserved contact endpoint')
                if k=='location' and isinstance(v,str) and ('@' in v or '://' in v):
                    check(reserved_endpoint('website' if '://' in v else 'email',v),f'{domain}: non-reserved contact endpoint')
                if (k.endswith('_at') or k.endswith('_on')) and k not in PLANNING_DATE_FIELDS and v is not None:
                    try:d=dt.date.fromisoformat(v[:10]);check(start<=d<=anchor,f'{domain}: recorded event outside history {k}')
                    except ValueError:errors.append(f'{domain}: invalid date {k}')
            if r.get('completed_at') and r.get('created_at'):check(r['completed_at']>=r['created_at'],f'{domain}: completion before creation')
            if r.get('resolved_at'):check(r['resolved_at']>=r['opened_at'],f'{domain}: resolution before opening')
    if errors:return errors
    for domain,count_key in [('customers','customers'),('leads','leads'),('talent','talent'),('staff','staff')]:check(len(tables.get(domain,[]))==config[count_key],f'{domain}: configured count mismatch')
    names=[r['display_name'] for r in tables['talent']];check(len(names)==len(set(names)),'duplicate fictional talent names')
    pairs=[(r['talent_id'],r['skill_id']) for r in tables['talent_skills']];check(len(pairs)==len(set(pairs)),'duplicate normalized talent skill')
    won=[r for r in tables['leads'] if r['status']=='won'];check(len(won)==len(tables['customers']),'won leads do not match paying customers')
    paid_by_customer=collections.Counter()
    for p in tables['payments']:
        paid_by_customer[p['customer_id']]+=p['amount_cents'];inv=index['invoices'][p['invoice_id']]
        check(p['customer_id']==inv['customer_id'],'payment customer differs from invoice')
        check(p['paid_on']>=inv['issued_on'],'payment precedes issue')
    for customer in tables['customers']:
        check(paid_by_customer[customer['id']]>0,'customer without a posted synthetic payment')
        lead=index['leads'][customer['lead_id']];check(lead['status']=='won','customer linked to non-won lead')
        check(customer['converted_on']>=lead['created_at'][:10],'customer conversion before lead')
    for contract in tables['contracts']:
        check(sum(r['line_total_cents'] for r in tables['contract_lines'] if r['contract_id']==contract['id'])==contract['amount_cents'],'contract line reconciliation failed')
        check(sum(r['amount_cents'] for r in tables['billing_schedule'] if r['contract_id']==contract['id'])==contract['amount_cents'],'billing schedule reconciliation failed')
        check(contract['ends_on']>=contract['starts_on']>=contract['signed_on'],'contract date order invalid')
    for invoice in tables['invoices']:
        iid=invoice['id'];line_total=sum(r['line_total_cents'] for r in tables['invoice_lines'] if r['invoice_id']==iid)
        paid=sum(r['amount_cents'] for r in tables['payments'] if r['invoice_id']==iid)
        credits=sum(r['amount_cents'] for r in tables.get('credit_notes',[]) if r['invoice_id']==iid)
        check(line_total==invoice['subtotal_cents'],'invoice line reconciliation failed')
        check(invoice['subtotal_cents']+invoice['tax_cents']==invoice['total_cents'],'invoice gross mismatch')
        check(invoice['total_cents']-credits-paid==invoice['balance_cents'],'invoice balance mismatch')
        check(invoice['paid_cents']==paid and invoice['credit_cents']==credits,'invoice allocated totals mismatch')
        check(invoice['due_on']>=invoice['issued_on'],'invoice due before issue')
        check((invoice['status']=='paid')==(invoice['balance_cents']==0),'invoice paid status mismatch')
    for domain in ('invoice_lines','contract_lines'):
        for r in tables[domain]:check(r['quantity']*r['unit_price_cents']==r['line_total_cents'],f'{domain}: line arithmetic failed')
    for m in tables['meetings']:
        check(m['ends_at']>m['starts_at'],'meeting duration invalid')
        future=m['starts_at'][:10]>config['anchor_date']
        check((m['status']=='scheduled')==future,'meeting status conflicts with anchor')
        check(m['notifications_sent'] is False,'meeting claims notification sent')
        check(index['contacts'][m['contact_id']]['account_id']==m['account_id'],'meeting contact belongs to different account')
    check(sum(m['status']=='scheduled' for m in tables['meetings'])==config['future_meetings'],'future meeting count mismatch')
    graph=collections.defaultdict(list)
    for r in tables['task_dependencies']:graph[r['task_id']].append(r['depends_on_task_id'])
    visiting=set();seen=set()
    def visit(node):
        if node in visiting:return False
        if node in seen:return True
        visiting.add(node)
        if not all(visit(n) for n in graph[node]):return False
        visiting.remove(node);seen.add(node);return True
    check(all(visit(n) for n in list(graph)),'task dependency cycle')
    return errors

def validate_directory(data,profiles=None):
    data=Path(data);manifest=json.loads((data/'manifest.json').read_text());meta=json.loads((data/'profile-provenance.json').read_text())
    tables={p.stem:[json.loads(x) for x in p.read_text().splitlines()] for p in sorted((data/'json').glob('*.jsonl'))}
    expected_domains=set(LINKS)|{'company','accounts','campaigns','knowledge','services','skills','talent'}
    errors=[]
    if set(tables)!=expected_domains:
        errors.append('JSON domains mismatch: missing='+str(sorted(expected_domains-set(tables)))+' extra='+str(sorted(set(tables)-expected_domains)))
    if not errors:
        errors.extend(validate_tables(tables,meta['config']))
    manifest_paths=set()
    for e in manifest['files']:
        relative=Path(e['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() in manifest_paths:
            errors.append('invalid or duplicate manifest path: '+e['path']);continue
        manifest_paths.add(relative.as_posix())
        p=data/relative
        if not p.is_file() or p.is_symlink() or p.stat().st_size!=e['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:
            errors.append('manifest mismatch: '+e['path'])
    actual_paths={p.relative_to(data).as_posix() for p in data.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if actual_paths!=manifest_paths:
        errors.append('manifest inventory mismatch: missing='+str(sorted(manifest_paths-actual_paths))+' extra='+str(sorted(actual_paths-manifest_paths)))
    if {k:len(v) for k,v in tables.items()}!=manifest['counts']:errors.append('manifest record counts mismatch')
    for domain,rows in tables.items():
        csv_path=data/'csv'/f'{domain}.csv'
        if not csv_path.is_file():errors.append('missing CSV: '+domain);continue
        with csv_path.open(newline='') as f:converted=list(csv.DictReader(f))
        if len(converted)!=len(rows):errors.append('CSV count mismatch: '+domain);continue
        for a,b in zip(rows,converted):
            if any(b.get(k)!=csv_value(v) for k,v in a.items()):errors.append('CSV/JSON mismatch: '+domain);break
    shapes=json.loads(Path(profiles or Path(__file__).parent/'inputs/profile-shapes.json').read_text())
    expected_titles=collections.Counter();expected_skills=collections.Counter()
    for shape in shapes['shapes']:
        expected_titles[shape['title']]+=shape['count']
        for skill in set(shape['skills']):expected_skills[skill]+=shape['count']
    if dict(expected_titles)!=meta['title_counts']:errors.append('title distribution differs from profile input')
    if dict(expected_skills)!=meta['skill_incidence_counts']:errors.append('skill incidence differs from normalized profile input')
    return {'synthetic':True,'status':'PASS' if not errors else 'FAIL','dataset_id':manifest['dataset_id'],'domain_count':len(tables),'record_count':sum(map(len,tables.values())),'counts':manifest['counts'],'checks':['synthetic markers','stable ID uniqueness','all declared references','date/status chronology','reserved contact endpoints','paying customer evidence','invoice/credit/payment arithmetic','contract/billing schedules','meeting containment','task DAG','CSV/JSON parity','manifest hashes and inventory','source-shape distributions'],'errors':errors,'live_import_attempted':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--receipt',type=Path);p.add_argument('--profiles',type=Path);a=p.parse_args();result=validate_directory(a.data,a.profiles)
    if a.receipt:a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='PASS' else 1)
if __name__=='__main__':main()
