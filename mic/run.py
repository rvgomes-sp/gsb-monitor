"""Pure orchestration. Dependencies and data are injected; no external side effects by default."""
from .engine import MicEngine,serialize

def run_offline(records,transport,catalogs,namespace_rule,namespace_rule_version):
    return serialize(MicEngine(transport,catalogs,namespace_rule,namespace_rule_version).run(records))
