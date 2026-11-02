import geopandas as gpd
import pytest
import pandas as pd
from shapely.geometry import Point
from governance.protected_areas.critical_habitat.normalize import normalize as habitat
from governance.shared.config import load_governance_config




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


def test_habitat_publisher_string_dates_and_blank_preserve_raw_evidence():
    values=['02/11/2015','03/25/2016','20210521',' ','2021-09-01']
    frame=gpd.GeoDataFrame([{'OBJECTID':i,'EFFECTDATE':value,'geometry':Point(-123,48)}
                           for i,value in enumerate(values)],crs=4326)
    frame.attrs['layer_metadata']={'fields':[{'name':'EFFECTDATE','type':'esriFieldTypeString'}]}
    result=habitat(frame,load_governance_config().sources['noaa_critical_habitat_polygon'])
    assert result.EFFECTIVE_START.iloc[:3].tolist()==['2015-02-11','2016-03-25','2021-05-21']
    assert pd.isna(result.EFFECTIVE_START.iloc[3])
    assert result.EFFECTIVE_START.iloc[4]=='2021-09-01'
    assert result.NOAA_EFFECTDATE.iloc[:3].tolist()==values[:3]
    assert frame.attrs['layer_metadata']['fields'][0]['type']=='esriFieldTypeString'
    assert frame.EFFECTDATE.tolist()==values
    frame['EFFECTDATE']=frame['EFFECTDATE'].astype(object)
    for value in ('02/30/2015','20210230','31/01/2015','2015','nonsense',1590969600000):
        frame.loc[0,'EFFECTDATE']=value
        with pytest.raises(ValueError):habitat(frame,load_governance_config().sources['noaa_critical_habitat_polygon'])
    frame.loc[0,'EFFECTDATE']='02/11/2015'
    frame.attrs['layer_metadata']['fields'][0]['type']='esriFieldTypeDate'
    with pytest.raises(ValueError):habitat(frame,load_governance_config().sources['noaa_critical_habitat_polygon'])
