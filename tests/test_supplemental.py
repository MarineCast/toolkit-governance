import geopandas as gpd
import pytest
import pandas as pd
from shapely.geometry import Point
from governance.administrative_context.ports.normalize import coordinate,source_frame,normalize as ports
from governance.protected_areas.critical_habitat.normalize import normalize as habitat
from governance.shared.config import load_governance_config


def test_port_dms_carry_and_no_legal_jurisdiction():
    assert coordinate('129°60\'00"W',latitude=False)==-130
    with pytest.raises(ValueError):coordinate('129°61\'00"W',latitude=False)
    with pytest.raises(ValueError):coordinate('48°00\'00"W',latitude=True)
    payload={'ports':[{'portNumber':42,'portName':'Reference','latitude':'48°30\'00"N','longitude':'123°00\'00"W','tss':'U'}]}
    frame=source_frame(payload)
    result=ports(frame,load_governance_config().sources['nga_world_port_index'])
    assert result.geometry.iloc[0]==Point(-123,48.5)
    assert result.JURISDICTION.iloc[0] is None
    assert result.LEGAL_AUTHORITY.iloc[0] is None
    assert result.NGA_tss.iloc[0]=='U'
    assert not result.MODEL_ELIGIBLE.any()
    with pytest.raises(ValueError):source_frame({'ports':payload['ports']*2})


def test_habitat_preserves_entity_status_and_source_date():
    frame=gpd.GeoDataFrame([{'OBJECTID':1,'LISTENTITY':'Entity A','CHSTATUS':'Proposed','EFFECTDATE':None,'geometry':Point(-123,48)}, {'OBJECTID':2,'LISTENTITY':'Entity B','CHSTATUS':'Designated','EFFECTDATE':'2021-09-01','geometry':Point(-123,48)}],crs=4326)
    result=habitat(frame,load_governance_config().sources['noaa_critical_habitat_polygon'])
    assert result.NOAA_CHSTATUS.tolist()==['Proposed','Designated']
    assert result.NOAA_LISTENTITY.tolist()==['Entity A','Entity B']
    assert pd.isna(result.EFFECTIVE_START.iloc[0])
    assert result.EFFECTIVE_START.iloc[1]=='2021-09-01'
    other=habitat(frame,load_governance_config().sources['noaa_critical_habitat_line'])
    assert not set(result.SOURCE_FEATURE_ID) & set(other.SOURCE_FEATURE_ID)
    assert result.LEGAL_BINDING_STATUS.tolist()==['reference_geometry']*2
    assert result.GOVERNANCE_FEATURE_ID.nunique()==2
