"""Species-neutral native-geometry marine governance products."""
from .shared.config import GovernanceConfig, load_governance_config
from .workspace import initialize_workspace

__version__ = '0.2.0'
__all__ = ['GovernanceConfig', 'load_governance_config', 'initialize_workspace']

from .query import GovernanceResult, get_layer, LayerNotImplementedError
from . import query as _query
for _name in dir(_query):
    if _name.startswith('get_'):
        globals()[_name] = getattr(_query, _name)
        __all__.append(_name)
__all__ += ['GovernanceResult', 'LayerNotImplementedError']
