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


@pytest.mark.parametrize('field,value,passes',[
 ('mean_forecast_walk_probability','0.16855951281711777',True),
 ('q_total','604',False),('realised_total_cost','64255.1900000001',False),
 ('mean_forecast_walk_probability','NaN',False)])
def test_aggregate_ratio_tolerance_preserves_counts_and_costs(tmp_path,field,value,passes):
    from hotel_cancel.csv_parity import compare_aggregate_table
    columns=['hotel','q_total','realised_total_cost','mean_forecast_walk_probability']
    row=['City Hotel','603','64255.19','0.16855951281711776'];changed=row.copy();changed[columns.index(field)]=value
    path=tmp_path/'aggregate.csv'
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(columns);writer.writerow(changed)
    reference={'columns':columns,'rows':[row]}
    if passes:assert compare_aggregate_table(reference,path)['all_counts_costs_and_labels_exact']
    else:
        with pytest.raises(ValueError):compare_aggregate_table(reference,path)
