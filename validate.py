import argparse
import os
import re
import sys

import xmltodict
from actions_toolkit import core


def find_keys(node, kv):
    if isinstance(node, list):
        for i in node:
            yield from find_keys(i, kv)
    elif isinstance(node, dict):
        if kv in node:
            yield node[kv]
        for j in node.values():
            yield from find_keys(j, kv)


def find_key_value(node, key, value):
    if isinstance(node, list):
        for i in node:
            yield from find_key_value(i, key, value)
    elif isinstance(node, dict):
        if key in node and value in node[key]:
            yield node
        for j in node.values():
            yield from find_key_value(j, key, value)


def find_dummy(node, key, value):
    if isinstance(node, list):
        for i in node:
            yield from find_dummy(i, key, value)
    elif isinstance(node, dict):
        if key in node:
            if isinstance(node.get(key, {}), dict):
                if node.get(key, {}).get('@classes') == value:
                    yield node[key]['inline']
        for j in node.values():
            yield from find_dummy(j, key, value)


def find_attribute_value(section, req_id, attribute):
    node = list(find_key_value(section, '@classes', 'needs_meta'))
    need_data = find_need_data(node, attribute)

    if need_data is None:
        return find_content_sub_directive(section, req_id, attribute)
    else:
        return need_data


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


def extract_req_type(section):
    classes = list(find_key_value(
        section, '@classes', 'needs_type_'))[0]['@classes']
    return re.findall("needs_type_\s*(.*)", classes)[-1]


def find_content_sub_directive(section, req_id, attribute):
    directive_by_id = list(
        find_key_value(section, '@ids', req_id))[1]
    sub_directive = list(find_key_value(
        directive_by_id, '@classes', 'needs_type_' + attribute))
    if len(sub_directive) > 0:
        need_content = list(find_key_value(sub_directive,
                                           '@classes', 'need content'))[0]
        content = list(find_keys(need_content, 'paragraph'))

        return content[0] if len(content) > 0 else None


def validate(target_file, requirements_dir, xmls_dir, errors):
    file_errors = []
    source = xmltodict.parse(open(os.path.join(xmls_dir, target_file)).read())

    sections = list(find_keys(list(find_keys(source, 'document'))[
                    0]['section'], 'section'))[0]

    for section in sections:
        metadata = list(find_key_value(section, '@classes', 'needs_meta'))

        artifact_type = find_need_data(metadata, 'artifact_type')

        if artifact_type is None or artifact_type in ['Information', 'Heading']:
            continue
        else:
            attribute_errors = []

            req_id = list(find_keys(section, 'target'))[0]['@ids']
            req_type = extract_req_type(section)

            for attribute in ['status', 'safety_level', 'verify', 'crq']:
                value = find_attribute_value(section, req_id, attribute)

                if value is None:
                    attribute_errors.append(attribute)

                if attribute == 'status' and value == 'Accepted':
                    allocation = find_attribute_value(
                        section, req_id, 'allocation')
                    if allocation is None:
                        attribute_errors.append('allocation')

            if len(attribute_errors) > 0:
                file_errors.append((req_type, req_id, attribute_errors))

    if len(file_errors) > 0:
        errors.append((os.path.join(requirements_dir, target_file.replace('.xml', '.rst')),
                      file_errors))


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
    requirements_dir, xml_folder_dir = init_arguments()

    xmls_dir = os.path.join(xml_folder_dir, os.path.split(requirements_dir)[1])

    errors = []

    for f in os.listdir(xmls_dir):
        validate(f, requirements_dir, xmls_dir, errors)

    if len(errors) > 0:
        for path, error in errors:
            core.error(format_message_error(path, error))
        sys.exit(1)
