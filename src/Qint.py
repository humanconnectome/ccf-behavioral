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

# %% [markdown]
# ### Purpose
# This program gathers all of the new raw Q-interactive data from Box and appends it to current snapshot

# %% pycharm={"is_executing": false}
from importlib import reload
from IPython.display import display
from numpy import nan
import pandas as pd

import PandasHelper as ph
from QintHelper import Qint
qint = Qint()

from download.redcap import RedcapTable
table = RedcapTable.get_table_by_name('qint')

# %%
# scan box to generate an up-to-date filelist. Note: Takes a few minutes
filelist = qint.scan_box()
filelist.head(3)

# %% pycharm={"is_executing": false}
cached_filelist = pd.read_csv('qint_files.csv')
cached_filelist.head(3)

# %% pycharm={"is_executing": false}
ph.asInt([filelist,cached_filelist], 'fileid')

# %% pycharm={"is_executing": false}
merged_filelist = cached_filelist.merge(filelist, 'right', on=['fileid'], suffixes=['_old','']) 
fresh_files = merged_filelist[merged_filelist.sha1_old.isna()]
updated_files = merged_filelist[merged_filelist.sha1_old.notna()]

# %% pycharm={"is_executing": false}
# Please deal with these rows that updated content
updated_content = updated_files[updated_files.sha1_old != updated_files.sha1]
updated_content

# %% pycharm={"is_executing": false}
# Please deal with these rows that have a name change. This might mean deleting the an existing row in redcap.
# todo: make sure that that updated_content and updated_names do not overlap otherwise concat below will contain duplicates
updated_names = updated_files[updated_files.filename_old != updated_files.filename]
updated_names

# %% pycharm={"is_executing": false}
fetchlist = pd.concat([fresh_files, updated_content, updated_names])
fetchlist = fetchlist[['created','fileid','filename','sha1']]
fetchlist.head()

# %% pycharm={"is_executing": false}
updates = qint.get_data(fetchlist.fileid)
db = qint.elongate(updates)

# %%
updates = pd.concat(db.values(), ignore_index=True, sort = False)
ph.asInt(updates, 'fileid', 'visit', 'ravlt_two')
updates.head(2)

# %%
current_redcap = table.get_frame(forms=['common'])
ph.asInt(current_redcap, 'visit', 'id')
current_redcap.head(2)

# %%
merged_redcap = current_redcap[['id','subjectid','visit', 'sha1']].merge(updates, 'right', on=['subjectid','visit'], suffixes=['.redcap',''])
merged_redcap.head(2)

# %%
is_identical = merged_redcap['sha1.redcap'] == merged_redcap.sha1
identical = merged_redcap[is_identical]
print('Ignoring %s rows with identical subject id, visit, and sha1' % len(identical))

changes = merged_redcap[~is_identical]
changes = changes.drop(columns=['sha1.redcap'])
print('Continuing with %s non-identical rows' % len(changes))

# %%
changes

# %%
has_redcap_id = changes.id.notna()

overwrite_old_rows = changes[has_redcap_id]
create_new_rows = changes[~has_redcap_id]
create_new_rows['id'] = table.generate_next_record_ids(len(create_new_rows))

changes = pd.concat([overwrite_old_rows, create_new_rows])

# %%
create_new_rows

# %%
changes

# %%
submission = table.send_frame(changes)

if (submission.status_code == 200):
    print('Updates were successful.')

submission.content

# %%

# %%
cached_filelist = cached_filelist[['created', 'fileid', 'filename', 'sha1']]
new_files_list = cached_filelist.append(updates[['created', 'fileid', 'filename', 'sha1']], sort=False)
new_files_list.to_csv('qint_files2.csv', index=False)

# %%

# %%
