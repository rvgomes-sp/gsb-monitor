"""Offline proof using preserved official pages. Explicit paths; zero network.

Outputs are audit artifacts in a NEW external directory, never the repository
or the operational database. Replays the exact same manifest twice.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import socket
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evt007.__main__ import main
from evt007.contracts import SOURCE, digest


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists(): raise ValueError('New audit directory required')
    args.out.mkdir(parents=True)
    def forbidden(*a,**k): raise RuntimeError('Network forbidden in Gate B replay')
    socket.create_connection=forbidden
    pages=[]
    for p in sorted(args.raw_dir.glob('pagina_*.json')):
        pages.append({'page':int(p.stem.split('_')[-1]),'path':str(p.resolve()),'sha256':digest(p.read_bytes())})
    if not pages: raise ValueError('No preserved pages')
    manifest={'source':SOURCE,'window':'2026-07-17','page_size':500,'pages':pages,
              'custody':'User-preserved V2.5 archive; no API call in this replay'}
    path=args.out/'manifest.json'; path.write_text(json.dumps(manifest,indent=2)+'\n')
    ledger=args.out/'proof.sqlite'
    outputs=[]
    for command in (["init-ledger","--ledger",str(ledger)],
                    ["replay","--manifest",str(path),"--ledger",str(ledger),"--max-pages","16"],
                    ["replay","--manifest",str(path),"--ledger",str(ledger),"--max-pages","16"]):
        stream=io.StringIO()
        print('Audit phase: '+command[0],file=sys.stderr,flush=True)
        with contextlib.redirect_stdout(stream): code=main(command)
        print('Audit phase completed: '+command[0],file=sys.stderr,flush=True)
        outputs.append({'exit_code':code,'result':json.loads(stream.getvalue())})
    first,second=outputs[1]['result'],outputs[2]['result']
    conn=sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True)
    try:
        integrity=[r[0] for r in conn.execute('PRAGMA integrity_check')]
    finally:
        conn.close()
    if integrity!=['ok']: raise RuntimeError('Replay ledger integrity failed')
    stable={key:first['ledger_counts'][key]==second['ledger_counts'][key]
            for key in ('events','revisions','candidate_cases','decisions')}
    summary={'executions':outputs,'idempotent_business_tables':stable,'sqlite_integrity_check':integrity,
             'new_live_requests':0,'operational_writes':0}
    (args.out/'replay_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if not all(stable.values()): raise SystemExit('Idempotency failed')


if __name__=='__main__': run()
