from IPython.core.display import display, HTML
from collections.abc import Iterable
from pandas import DataFrame, Series


def __as_dataframe__(pandas_item):
    if isinstance(pandas_item, Series):
        return pandas_item.to_frame()
    elif not isinstance(pandas_item, DataFrame):
        raise TypeError('Expecting either a Series or DataFrame')
    return pandas_item


def __column_name_parameters_helper__(data, column_names=None, column_names2=None):
    data = __as_dataframe__(data)

    column_names = column_names or column_names2

    if column_names:

        # if only a single column is provided, convert to one item set
        # else convert iterable into set
        column_names = {column_names} \
            if isinstance(column_names, str) or not isinstance(column_names, Iterable) \
            else set(column_names)

        return data[column_names].copy()
    else:
        return data.copy()


def __diff__(df1, df2, indicator='_merge'):
    result = df1.merge(df2, how='left', indicator=indicator)
    return result[result[indicator] == 'left_only']


def __intersection__(df1, df2, indicator='_merge'):
    return df1.merge(df2, how='inner', indicator=indicator)


def __symmetric_diff__(df1, df2, indicator='_merge'):
    result = df1.merge(df2, how='outer', indicator=indicator)
    return result[result[indicator] != 'both']


def __reelongate__(filter_func, df1, df2, on=None, left_on=None, right_on=None, equal_names=True, indicator='_merge',
                   sources=None,
                   drop_duplicates=True, drop_indicator=False):
    df1, df2 = __as_dataframe__(df1), __as_dataframe__(df2)

    a = __column_name_parameters_helper__(df1, left_on, on)
    b = __column_name_parameters_helper__(df2, right_on, on)
    if equal_names:
        columns_in_common = a.columns.intersection(b.columns)
        a = a[columns_in_common]
        b = b[columns_in_common]
        filter = filter_func(a, b, indicator)

        a = df1.merge(filter[filter[indicator] != 'right_only'], 'right')
        b = df2.merge(filter[filter[indicator] != 'left_only'], 'right')
    else:
        minimum = min(len(a.columns), len(b.columns))
        a = a.iloc[:, :minimum]
        b = b.iloc[:, :minimum]
        old_b_cols_map = dict(zip(a.columns, b.columns))
        b.columns = a.columns
        filter = filter_func(a, b, indicator)

        a = df1.merge(filter[filter[indicator] != 'right_only'], 'right')
        filter = filter.rename(columns=old_b_cols_map)
        b = df2.merge(filter[filter[indicator] != 'left_only'], 'right')

    a[indicator], b[indicator] = sources if sources else ('left', 'right')

    result = a.append(b, sort=False).sort_values(filter.columns.to_list())

    if drop_duplicates:
        result.drop_duplicates(subset=result.columns[:-1], keep=False, inplace=True)

    if drop_indicator:
        result = result.iloc[:, :-1]

    return result


def diff(df1, df2, on=None, left_on=None, right_on=None, equal_names=True, indicator='_merge', sources=None,
         drop_duplicates=True, drop_indicator=True):
    return __reelongate__(__diff__, df1, df2, on, left_on, right_on, equal_names, indicator, sources, drop_duplicates, drop_indicator)


def intersection(df1, df2, on=None, left_on=None, right_on=None, equal_names=True, indicator='_merge', sources=None,
                 drop_duplicates=True):
    return __reelongate__(__intersection__, df1, df2, on, left_on, right_on, equal_names, indicator, sources,
                          drop_duplicates)


def symmetric_diff(df1, df2, on=None, left_on=None, right_on=None, equal_names=True, indicator='_merge', sources=None,
                   drop_duplicates=True):
    return __reelongate__(__symmetric_diff__, df1, df2, on, left_on, right_on, equal_names, indicator, sources,
                          drop_duplicates)

def series_is_equal(series):
    return series.duplicated(keep=False).all()

def unequal_columns(df):
    """ Find the name of the columns that are unequal
    """
    unequal = [colname for colname, value in df.iteritems() if not series_is_equal(value)]
    return unequal

def showbox(message, heading=None, type='success'):
    box = '<div class="alert alert-%s" role="alert">' % type
    if heading:
        box += '<h4 class="alert-heading">%s</h4>' % heading
    box += '<p>%s</p></div>' % message
    return display(HTML(box))


def showdataframe(df):
    if not df.empty:
        print('Size: r%s x c%s' % df.shape)
        display(df[:3])


def asInt(dfs, *columns):
    if isinstance(dfs, DataFrame):
        dfs = [dfs]
    for df in dfs:
        for column in columns:
            df[column] = df[column].astype(float).astype('Int64')
