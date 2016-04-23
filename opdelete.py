import pprint

__author__ = 'Volodymyr Varchuk'
__email__ = "vladimir.varchuk@rackspace.com"

from util import *


# UPDATE_TMPL2 = 'UPDATE %s SET %s WHERE (root_id="%s") and (idx=%s);'
# {"template":'UPDATE table SET idx=34 WHERE idx=%s;', "params":['45']}


def op_delete_stmts(schema, path, id):
    return gen_statements(schema, path, id)


def get_max_id_in_array(path):
    # stub
    #
    # get max index of element in array corresponding for deleted record

    return '10'


def get_child_dict_item(dict_items, table):
    tables_list = []
    for it in dict_items:
        if type(dict_items[it]) is dict:
            # TODO fix last letter in dictionary
            tables_list = get_child_dict_item(dict_items[it], table[:-1] + '_' + it)
        elif type(dict_items[it]) is list:
            tables_list = get_tables_list(dict_items[it], table[:-1] + '_' + it)
    return tables_list


def get_tables_list(schema, table):
    tables_list = []
    tables_list.append(table)
    for item_list in schema:
        if type(item_list) is dict or type(item_list) is list:
            for it in item_list:
                item_value = item_list[it]
                if type(item_value) is dict:
                    # TODO last letted in dictioonary
                    tables_list.extend(get_child_dict_item(item_value, table[:-1] + '_' + it))
                elif type(item_value) is list:
                    tables_list.extend(get_tables_list(item_value, table[:-1] + '_' + it))
    return tables_list


def get_conditions_list(schema, path, id):
    spath = path.split('.')
    parental_tables_list = get_indexes_dictionary(path)
    parental_tables_idx_list = get_indexes_dictionary_idx(path)
    target_table = get_table_name_from_list(spath)
    target_table_idxname_for_child = get_idx_column_name_from_list(spath)
    params_target = {}
    for it in parental_tables_idx_list:
        if target_table_idxname_for_child <> it:
            params_target[it + '_idx'] = parental_tables_idx_list[it]

    ids = get_ids_list(schema)
    root_id = ids.iterkeys().next()
    root_table = get_root_table_from_path(path)

    params_child = params_target.copy()

    if root_table == target_table:
        params_target[root_id] = id
        params_child[target_table_idxname_for_child + '_' + root_id] = id
    else:
        params_target[root_table + '_' + root_id] = id
        params_child[root_table + '_' + root_id] = id
        if target_table_idxname_for_child in parental_tables_idx_list.keys():
            params_target['idx'] = parental_tables_idx_list[target_table_idxname_for_child]
            params_child[target_table_idxname_for_child + '_idx'] = parental_tables_idx_list[target_table_idxname_for_child]
    return {'target': params_target, 'child': params_child}


def get_where_templates(conditions_list):
    # TODO check id`s types. compliance quotes
    def condition_with_quotes(key):
        temp = ''
        if key.endswith('_idx') or key == 'idx':
            temp = '({0}=%s)'.format(key)
        else:
            temp = '({0}="%s")'.format(key)
        return temp

    where_list = {'target': {}, 'child': {}}
    where_list['target']['template'] = ' and '.join(sorted([(condition_with_quotes(key)) for key in conditions_list['target']]))
    where_list['target']['values'] = [conditions_list['target'][key] for key in sorted(conditions_list['target'])]
    where_list['child']['template'] = ' and '.join(sorted([(condition_with_quotes(key)) for key in conditions_list['child']]))
    where_list['child']['values'] = [conditions_list['child'][key] for key in sorted(conditions_list['child'])]

    return where_list


def gen_statements(schema, path, id):
    where_clauses = get_where_templates(get_conditions_list(schema, path, id))
    all_tables_list = get_tables_list(schema, get_root_table_from_path(path))
    target_table = get_table_name_from_list(path.split('.'))
    target_table_idx_name = get_idx_column_name_from_list (path.split('.'))
    tables_list = []
    for table in all_tables_list:
        if str.startswith(str(table), target_table[:-1], 0, len(table)) and not table == target_table:
            tables_list.append(table)
    del_statements = {}
    del_statements[DELETE_TMPLT.format(table=target_table, conditions=where_clauses['target']['template'])] = \
        where_clauses['target']['values']
    for table in tables_list:
        del_statements[DELETE_TMPLT.format(table=table, conditions=where_clauses['child']['template'])] = \
            where_clauses['child']['values']
    update_statements = {}
    idx = get_last_idx_from_path(path)
    max_idx = get_max_id_in_array(path)
    if idx <= max_idx:
        return {'del': del_statements, 'upd': update_statements}

    for ind in range(int(idx) + 1, int(max_idx) + 1):
        spath = path.split('.')
        del spath[-1]
        spath.append(str(ind))
        path_to_update = '.'.join(spath)
        udpate_where = get_where_templates(get_conditions_list(schema, path_to_update, id))
        update_statements[UPDATE_TMPLT.format(table=target_table, statements='idx=' + str(ind - 1),
                                             conditions=udpate_where['target']['template'])] = udpate_where['target'][
            'values']

        for table in tables_list:
            update_statements[UPDATE_TMPLT.format(table=table, statements=target_table_idx_name + '_idx=' + str(ind - 1),
                                                 conditions=udpate_where['child']['template'])] = udpate_where['child'][
                'values']
    return {'del': del_statements, 'upd': update_statements}
