import csv
import pytest
from hotel_cancel.csv_parity import COLUMNS,compare_nightly_csv


def pair(tmp_path,field,value):
    row=['City Hotel','2017-01-01','reference policy','2','3.8814563928873946','1','1','0','250.0']
    paths=[tmp_path/'reference.csv',tmp_path/'actual.csv']
    for i,path in enumerate(paths):
        changed=row.copy()
        if i:changed[COLUMNS.index(field)]=value
        with path.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(COLUMNS);writer.writerow(changed)
    return paths


def test_machine_precision_difference_is_allowed_only_in_expected_sum(tmp_path):
    result=compare_nightly_csv(*pair(tmp_path,'expected','3.881456392887394'))
    assert result['all_other_columns_exact'] and result['changed_expected_cells']==1
    assert result['maximum_absolute_expected_difference']==6e-16


@pytest.mark.parametrize('field,value',[('q','3'),('cost','250.0000000000001'),('policy','other policy'),('expected','3.8814564'),('expected','NaN')])
def test_decision_cost_policy_or_material_numeric_changes_fail(tmp_path,field,value):
    with pytest.raises(ValueError):compare_nightly_csv(*pair(tmp_path,field,value))
