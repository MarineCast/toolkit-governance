"""Historical popup facts cannot leak onto a different source or reporting grid."""
import copy
import hashlib

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from governance.vessel_management.exclusion_zones.replay import MASK_LIMITATION, grid_digest, replay_qualifications


@pytest.fixture
def replay_input(tmp_path):
    path = tmp_path/'source.parquet'
    pq.write_table(pa.table({'ID':['zone'], 'geometry':[b'original-geometry']}), path)
    table = pa.table({'h3_index':['cell-a','cell-b']})
    fields = {name: {'support_limitation':MASK_LIMITATION, 'interpretation':MASK_LIMITATION}
              for name in ('exclusion_zones__recorded_feature_count','exclusion_zones__feature_memberships_v1')}
    metadata = {'spatial':{'h3_resolution':6},'sources':{'source':{'snapshot_sha256':'snapshot'}},
                'original_data':{'source':{'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}},'fields':fields}
    receipt = {'schema_version':1,'reviewed_at_utc':'2026-10-19','evidence':{'mask_sha256':'reviewed-mask'},
               'grids':{'6':{'rows':2,'sorted_h3_ids_sha256':grid_digest(['cell-a','cell-b'])}},
               'qualified_mask_limitation':'Reviewed distance for this source and native grid.',
               'records':{'zone':{'source_id':'source','identity_column':'ID','identity_value':'zone',
                                 'source_snapshot_sha256':'snapshot','geometry_wkb_sha256':hashlib.sha256(b'original-geometry').hexdigest(),
                                 'facts':{'study_water_mask_distance_m':'21.5','study_water_mask_intersection':'false'}}}}
    return table,metadata,receipt,tmp_path


def test_replays_exact_evidence_on_same_grid_independent_of_row_order(replay_input):
    table,metadata,receipt,root = replay_input
    context = {'zone':{'existing_qualification':'kept'}}
    replay_qualifications(table.take(pa.array([1,0])),metadata,root,context,receipt=receipt)
    assert context['zone'] == {'existing_qualification':'kept',**receipt['records']['zone']['facts']}
    assert metadata['fields']['exclusion_zones__recorded_feature_count']['support_limitation'] == receipt['qualified_mask_limitation']
    assert metadata['exclusion_zone_interface']['qualification_replay']['evidence']['mask_sha256']=='reviewed-mask'


@pytest.mark.parametrize('change',['grid','snapshot','geometry'])
def test_changed_support_does_not_inherit_historical_distance(replay_input,change):
    table,metadata,receipt,root = replay_input
    if change=='grid':table=pa.table({'h3_index':['cell-a','different-cell']})
    elif change=='snapshot':metadata['sources']['source']['snapshot_sha256']='new-snapshot'
    else:receipt=copy.deepcopy(receipt);receipt['records']['zone']['geometry_wkb_sha256']='different-geometry'
    context={'zone':dict(receipt['records']['zone']['facts'])}
    replay_qualifications(table,metadata,root,context,receipt=receipt)
    assert context['zone']=={}
    assert metadata['fields']['exclusion_zones__recorded_feature_count']['support_limitation']==MASK_LIMITATION
    assert 'exclusion_zone_interface' not in metadata


def test_corrupted_original_is_rejected(replay_input):
    table,metadata,receipt,root=replay_input
    metadata['original_data']['source']['sha256']='wrong'
    with pytest.raises(ValueError,match='checksum'):
        replay_qualifications(table,metadata,root,{'zone':{}},receipt=receipt)
