import xmltodict
import argparse
from actions_toolkit import core
import os


def find_keys(node, kv):
    if isinstance(node, list):
        for i in node:
            for x in find_keys(i, kv):
                yield x
    elif isinstance(node, dict):
        if kv in node:
            yield node[kv]
        for j in node.values():
            for x in find_keys(j, kv):
                yield x


def find_key_value(node, key, value):
    if isinstance(node, list):
        for i in node:
            for x in find_key_value(i, key, value):
                yield x
    elif isinstance(node, dict):
        if key in node and value in node[key]:
            yield node
        for j in node.values():
            for x in find_key_value(j, key, value):
                yield x


def find_dummy(node, key, value):
    if isinstance(node, list):
        for i in node:
            for x in find_dummy(i, key, value):
                yield x
    elif isinstance(node, dict):
        if key in node:
            if isinstance(node.get(key, {}), dict) and value == node.get(key, {}).get('@classes', None):
                yield node[key]['inline']
        for j in node.values():
            for x in find_dummy(j, key, value):
                yield x


def find_need_data(node, attribute):
    target = list(find_dummy(node, 'inline', 'needs_' + attribute))
    if len(target) > 0:
        return list(find_key_value(target[0], '@classes', 'needs_data'))[0]['#text']


def format_message_error(path, errors):
    message = path
    for id, type, attributes in errors:
        message += f'\n\t{id} - {type}'
        for attribute in attributes:
            message += f'\n\t\tERROR:field \'{attribute}\' must be filled'
    return message


def validate(target_file):
    errors = []
    source = xmltodict.parse(open(target_file).read())

    metadata = list(find_key_value(source, '@classes', 'needs_meta'))

    for i in metadata:
        artifact_type = find_need_data(i, 'artifact_type')
        if artifact_type is None or artifact_type in ['Information', 'Heading']:
            continue
        else:
            attribute_errors = []
            req_id = list(find_keys(i, '@reftitle'))[0]
            check = list(find_key_value(source, '@ids', req_id))
            if len(check) > 0:
                req_type = check[1]['@classes'].split('needs_type_')[1]
            for attribute in ['status', 'safety_level', 'verify', 'crq']:
                data = find_need_data(i, attribute)

                if data is None:
                    directive_by_id = list(
                        find_key_value(source, '@ids', req_id))[1]
                    sub_directive = list(find_key_value(
                        directive_by_id, '@classes', 'needs_type_verify'))
                    data = list(find_key_value(sub_directive,
                                               '@classes', 'need content'))[1].get('paragraph')

                    if data is None:
                        attribute_errors.append(attribute)

                if attribute == 'status' and data == 'Accepted':
                    allocation = find_need_data(i, 'allocation')
                    if allocation is None:
                        attribute_errors.append('allocation')
            if len(attribute_errors) > 0:
                errors.append((req_type, req_id, attribute_errors))

    if len(errors) > 0:
        return format_message_error(target_file, errors)


def init_arguments():
    """
    This function is used to get arguments from the command line.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--inputs",
        help="Path to the folder containing all the rst files",
    )

    parser.add_argument(
        '-xml',
        '--xml_output',
        help='Path to output after run sphinx builder xml'
    )

    args = parser.parse_args()
    return args.inputs, args.xml_output


if __name__ == '__main__':
    reqs_dir, xml_folder_dir = init_arguments()

    xmls_dir = os.path.join(xml_folder_dir, reqs_dir)

    messages = ''

    for f in os.listdir(xmls_dir):
        file_path = os.path.join(xmls_dir, f)
        messages += validate(file_path)

    if messages != '':
        core.set_failed(messages)
