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

# %% pycharm={"name": "#%%\n"}
# Downloading the lastest data from KSADS.net 
# takes more than 30 min
import DownloadKsads

DownloadKsads.main()
print('Done.')

# %%
from IPython.display import display, HTML
import ipysheet
import ipywidgets as wg
import os
import pandas as pd
import PandasHelper as h
from download.redcap import get_behavioral_ids, RedcapTable
from KsadsHelper import KSADS
import numpy as np
import re
from config import LoadSettings


# %%
def read_csv(date, form):
    return pd.read_csv(os.path.join(downloads_dir, date, form + '.csv'), low_memory=False)


# %% pycharm={"is_executing": false}
table = RedcapTable.get_table_by_name('ksads')
studyids = get_behavioral_ids()

# %% pycharm={"is_executing": false, "name": "#%%\n"}
config = LoadSettings()
downloads_dir = config['KSADS']['download_dir']
dates = sorted(os.listdir(downloads_dir))

olddate = dates[0]
newdate = dates[-1]

form = 'intro'
form_complete = f'{form}_complete'
old = read_csv(olddate, form)
new = read_csv(newdate, form)
redcap_df = table.get_frame(forms=['common', form])
redcap_df = redcap_df[redcap_df[form_complete] == 1]

# %%
deleted = h.diff(old, new.id)
modified = h.intersection(old, new, 'id').sort_values('id')
added = h.diff(new, old.id)
added[form_complete], added['common_complete'] = 1, 1
added = h.diff(added, redcap_df)

# %% pycharm={"is_executing": false, "name": "#%%\n"}
if added is not None and not added.empty:
    merged = redcap_df.append(added, sort=False)
else:
    merged = redcap_df

# %% pycharm={"name": "#%%\n"}
if not deleted.empty:
    display(HTML('<H3>Deleted Rows</H3><SMALL> The following rows have been deleted in the new data, compared to the previously available data. </SMALL>'))
    display(ipysheet.sheet(ipysheet.from_dataframe(deleted)))

# %% pycharm={"name": "#%%\n"}
if not modified.empty:
    display(HTML('<H3>Modified Rows</H3><SMALL> The following rows have been modified. </SMALL>'))
    display(ipysheet.sheet(ipysheet.from_dataframe(modified)))

# %%
# Show additional Info
show = added.dropna(subset=['additionalinfo']).iloc[:,:6]
if not show.empty:
    display(HTML('<H3>Additional Info </H3><SMALL> Please read the additional info columns for possible clarifications/corrections</SMALL>'))
    display(ipysheet.sheet(ipysheet.from_dataframe(show)))


# %%
def update(btn):
    global added
    added = dups.loc[[dd.value for dd in selections]].iloc[:,:-1].append(added, sort=False).drop_duplicates(['patientid','patienttype'])

btn = wg.Button(description = 'Submit changes')
btn.on_click(update)
    
dups = h.intersection(redcap_df, added, ['patientid','patienttype'], sources=('current','new')).reset_index(drop=True)
selections = []
output = []
for id, group in dups.groupby('id'):
    cols = ['id','patientid'] + h.unequal_columns(group)
    show = group[cols].set_index('_merge')
    sheet = ipysheet.sheet(ipysheet.from_dataframe(show))
    options = [(k,v) for v, k in group._merge.items()]

    dd = wg.Dropdown(
        options=options,
        value=options[0][1],
        description='Keep version:',
        disabled=False,
    )
    selections.append(dd)
    output.append(sheet)
    output.append(dd)

if output:
    display(HTML('<H3>Should New Data Overwrite Old Data</H3><SMALL>Please select which version to keep.</SMALL>'))
    for x in output:
        display(x)
    display(btn)

# %%
df = merged.copy()
df['subject'] = df['patientid'].str.split("_", 1, expand=True)[0].str.strip()
not_in_redcap = h.diff(df, studyids.subject).iloc[:,:-1]
h.asInt(not_in_redcap, 'id','common_complete', form_complete)
not_in_redcap.insert(0,'delete', False)
not_in_redcap.insert(1,'link', 'view')

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
    
    # delta  of changes
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

fancy_widget = wg.VBox([sheet, btns])

if not not_in_redcap.empty:
    display(HTML('<H3>Subject IDs not in Redcap</H3><SMALL>Please either change patientid to match an ID in redcap or delete the row.</SMALL>'))
    display(fancy_widget)

# %%
ipysheet.cell(0,1, wg.HTML('<a href="https://google.com">48598</a>'))


# %%
def convert_to_links():
    values = [wg.HTML(f'<a target="_blank" href="https://redcap.wustl.edu/redcap/redcap_v8.11.0/DataEntry/record_home.php?pid=3355&arm=1&id={x}">view</a>') for x in sheet.cells[2].value]
    ipysheet.column(1, values) 


# %%
remove_html()

# %%
convert_to_links()

# %%
ipysheet.column()

# %%
extract_rx = re.compile('<[^>]+>')


# %%
def remove_html():
    values = [extract_rx.sub('', x.value) for x in sheet.cells[1].value]
    ipysheet.column(1, values) 


# %%
df = ipysheet.to_dataframe(sheet)
df = df.replace('nan', np.nan)
df

# %%
values

# %%
studydata = studyids[studyids.study != 'hcpdparent']
missing = h.diff(studydata, df.subject)

# missing = h.difference(studydata, df.subject).copy()
missing = missing[missing.flagged.isnull()]
missing = missing[missing.interview_date < '2019-05-01']
missing = missing[missing.study != 'hcpa']
missing['reason'] = 'Missing in Box'
missing
# data['missing'] = missing
# ksads.warn_missing(missing, form)

# %% [markdown]
# # Screener

# %%
form = 'screener'
data = ksads.read_data(form)
overall[form] = data

# %%
data['merged'] = data['merged'].drop_duplicates(['patientid','patienttype'], keep='last')
df = data['merged']

# %%
df = data['merged']
df = df[['patientid', 'patienttype', 'sitename', 'additionalinfo']].copy()
df['subject'] = df['patientid'].str.split("_", 1, expand=True)[0].str.strip()

# %% [markdown]
# ### Additional Info
# Please read the additional info columns for possible clarifications/corrections:

# %%
data['added'].dropna(subset=['additionalinfo'])

# %% [markdown]
# ### Quality Control

# %%
duplicates = df[df.duplicated(['patientid', 'patienttype'], keep=False)]
duplicates['reason'] = 'Duplicate IDs'
data['duplicates'] = duplicates
ksads.warn_duplicates(duplicates, form)

# %%
not_in_redcap = h.difference(df, studyids.subject).copy()
not_in_redcap['reason'] = 'PatientID not in Redcap'
not_in_redcap.rename(columns={'sitename': 'site'}, inplace=True)
data['not_in_redcap'] = not_in_redcap
ksads.warn_not_in_redcap(not_in_redcap, form)

# %%
missing = h.difference(studydata, df.subject).copy()
missing = missing[missing.flagged.isnull()]
missing = missing[missing.interview_date < '2019-05-01']
missing = missing[missing.study != 'hcpa']
missing['reason'] = 'Missing in Box'
data['missing'] = missing
ksads.warn_missing(missing, form)

# %% [markdown]
# # Supplement

# %%
form = 'supplement'
data = ksads.read_data(form)
overall[form] = data

# %%
data['merged'] = data['merged'].drop_duplicates(['patientid','patienttype'])
df = data['merged']

# %%
df = data['merged']
df = df[['patientid', 'patienttype', 'sitename', 'additionalinfo']].copy()
df['subject'] = df['patientid'].str.split("_", 1, expand=True)[0].str.strip()

# %% [markdown]
# ### Additional Info
# Please read the additional info columns for possible clarifications/corrections:

# %%
data['added'].dropna(subset=['additionalinfo'])

# %% [markdown]
# ### Quality Control

# %%
duplicates = df[df.duplicated(['patientid', 'patienttype'], keep=False)]
duplicates['reason'] = 'Duplicate IDs'
data['duplicates'] = duplicates
ksads.warn_duplicates(duplicates, form)

# %%
not_in_redcap = h.difference(df, studyids.subject).copy()
not_in_redcap['reason'] = 'PatientID not in Redcap'
not_in_redcap.rename(columns={'sitename': 'site'}, inplace=True)
data['not_in_redcap'] = not_in_redcap
ksads.warn_not_in_redcap(not_in_redcap, form)

# %%
missing = h.difference(studydata, df.subject).copy()
missing = missing[missing.flagged.isnull()]
missing = missing[missing.interview_date < '2019-05-01']
missing = missing[missing.study != 'hcpa']
missing['reason'] = 'Missing in Box'
data['missing'] = missing
ksads.warn_missing(missing, form)


# %% [markdown]
# # Upload New Data

# %%

# %%
def put_data(d):
    return ksads.redcap.send_frame(d)


# %%
x = put_data(overall['intro']['added']).json()
len(x)

# %%
y = put_data(overall['screener']['added']).json()
len(y)

# %%
z = put_data(overall['supplement']['added']).json()
len(z)
