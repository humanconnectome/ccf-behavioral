# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: ccf_env
#     language: python
#     name: ccf_env
# ---

# %%
import numpy as np

from importlib import reload
from IPython.display import display
import pandas as pd
import ipysheet
import ipywidgets as wg

import PandasHelper as ph
from QintHelper import Qint
qint = Qint()

from download.redcap import RedcapTable, Redcap
redcap = Redcap()
table = RedcapTable.get_table_by_name('qint')

# %%
current_redcap = table.get_frame(forms=['common'])
# current_redcap = current_redcap.rename(columns={'subjectid': 'subject'})
current_redcap.head(2)

# %%
studyids = qint.get_subjects()
studydata = studyids[studyids.study != 'hcpdparent']

# %%
studyids2 = redcap.getredcapids()
studydata2 = redcap.getredcapdata()

# %%
excluded = studydata[(studydata.subject_id != studydata.subject)]
excluded.head()

# %%
not_in_redcap = ph.difference(current_redcap, studyids.subject,'subjectid', equal_names=False).copy()

# %%
not_in_redcap.insert(0,'delete', False)
sheet = ipysheet.sheet(ipysheet.from_dataframe(not_in_redcap))

spaced = wg.Layout(margin='30px 0 20px 0')

save_btn = wg.Button(description="Update", icon='save')
reset_btn = wg.Button(description="Reset", icon='trash')
btns = wg.HBox([save_btn, reset_btn], layout=spaced)

def on_reset(btn):
    sheet.cells= ipysheet.from_dataframe(not_in_redcap).cells
#     sheet = ipysheet.sheet(ipysheet.from_dataframe(not_in_redcap))
    
reset_btn.on_click(on_reset)

def on_update(btn):
    df = ipysheet.to_dataframe(sheet)
    df = df.replace('nan', np.nan)

    z = ph.difference(df, not_in_redcap)


    updates = z[~z.delete].iloc[:,1:]
    if not updates.empty:
        r = table.send_frame(updates)
        print('Updates: ',r.status_code, r.content)

    delete = z[z.delete].id.tolist()
    if delete:
        r = table.delete_records(delete)
        print('Delete Records: ',r.status_code, r.content)

save_btn.on_click(on_update)

fancy_widget = wg.VBox([wg.Label('Please update the subject id or delete the row.'), sheet, btns])
fancy_widget

# %%

# %%
current_redcap

# %%
allrowsofinterest = current_redcap[['subjectid', 'visit', 'assessment']]

combined = allrowsofinterest.merge(studyids, 'left', left_on='subjectid', right_on='subject')
notinredcap = combined.loc[combined.subject_id.isnull()].copy()
notinredcap['reason'] = 'PatientID not in Redcap'

notinredcap

# %%
combined = allrowsofinterest.merge(studydata, 'right', left_on='subjectid', right_on='subject')
notinboxunique = combined.loc[combined.assessment.isnull() & combined.flagged.isnull()].drop_duplicates('subject')
notinboxunique

# %% [markdown]
# # Make sure records are complete

# %%
status1 = redcap.getredcapfields(['data_status', 'misscat'], study='hcpdchild')
status1 = status1[['data_status', 'subject_id', 'misscat___9']].copy()
status1.columns = ['data_status', 'subject_id', 'misscat']

status2 = redcap.getredcapfields(['data_status', 'misscat'], study='hcpa')
status2 = status2[['data_status', 'subject_id', 'misscat___7']].copy()
status2.columns = ['data_status', 'subject_id', 'misscat']

status3 = redcap.getredcapfields(['data_status', 'misscat'], study='hcpd18')
status3 = status3[['data_status', 'subject_id', 'misscat___9']].copy()
status3.columns = ['data_status', 'subject_id', 'misscat']

tnotinboxunique = notinboxunique\
                    .merge(status1, 'left', 'subject_id', suffixes=('','_x'))\
                    .merge(status2, 'left', 'subject_id', suffixes=('','_y'))\
                    .merge(status3, 'left', 'subject_id', suffixes=('','_z'))

t = tnotinboxunique.copy()

t.data_status.mask(t.data_status.isnull(), t.data_status_y, inplace=True)
t.data_status.mask(t.data_status.isnull(), t.data_status_z, inplace=True)
t.misscat.mask(t.misscat.isnull(), t.misscat_y, inplace=True)
t.misscat.mask(t.misscat.isnull(), t.misscat_z, inplace=True)

t.drop(columns={'data_status_y','data_status_z','misscat_y','misscat_z'}, inplace=True)

t.loc[t.data_status.isna(), 'reason'] = 'Missing in Box - visit summary incomplete'
t.loc[t.data_status == 1, 'reason'] = 'Missing in Box - visit summary says complete '
t.loc[(t.data_status == 2) & (t.misscat != 1), 'reason'] = 'Missing in Box - visit summary says incomplete but cog testing not specified '
notinboxunique = t[(t.data_status != 2) | (t.misscat != 1)]

# %%
ph.asInt([status1, status2, status3], 'data_status', 'misscat')

# %%

# %%

# %%
studydata

# %%
# get list of ids that need visit numbers associated with files
needsvisit = current_redcap[current_redcap.visit.isna()]
needsvisit = needsvisit \
    .merge(studydata, 'left', 'subject') \
    .drop(columns={'dob', 'flagged', 'gender', 'subject_id'})
needsvisit['reason'] = 'please specify visit number'
needsvisit

# %%
catQC = pd.concat([notinredcap, notinboxunique, needsvisit], axis=0, sort=True)
catQC = catQC[['subject', 'interview_date', 'study', 'site', 'filename', 'reason', 'visit']]
catQC = catQC.sort_values(['site','study'])

# %%
catQC.shape

# %%
with open('qint_exclude_list.txt', 'r') as fd:
    excluded = fd.read().split()

# %%
# if known perminently deleted, then remove from list
catQC = catQC[~catQC.subject.isin(excluded)]

# %%
catQC.shape

# %%
catQC

# %%

# %%
