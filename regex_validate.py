import argparse
import os
import re

from actions_toolkit import core


class RegExValidator:
    def __init__(self, attr_names):
        self.attr_names = attr_names
        self.file_path = None
        self.requirements = None
        self.errors = None

    def get_requirements(self):
        """
        Get list of requirements content. Content of a requirement is indented to mark as a block.
        We based on this feature to collect information
        """
        self.requirements = []
        is_req_content = False
        with open(self.file_path, "r") as f:
            for line in f.readlines():
                if line.startswith(".. sw_req::"):
                    self.requirements.append(
                        {"type": "Software Requirement", "content": ""}
                    )
                    is_req_content = True
                elif line.startswith(".. sys_req::"):
                    self.requirements.append(
                        {"type": "System Requirement", "content": ""}
                    )
                    is_req_content = True
                elif line.startswith("   "):
                    if is_req_content:
                        self.requirements[-1]["content"] += line
                elif line == "\n":
                    continue
                else:
                    is_req_content = False
        return self.requirements

    def check_exist_empty(self, req, attr_name):
        """
        Given a requirement, check if an `attr_name` is exist and not empty.
        .. Args::
            :req: content of a requirement
            :attr_name: name of required attribute
        """
        if re.search(r":{}: (\S+)".format(attr_name), req):
            value = re.search(r":{}: (\S+)".format(attr_name), req).group(1)
            return True, value
        elif re.search(r".. {}::\s*(\S+)".format(attr_name), req):
            value = re.search(r".. {}::\s*(\S+)".format(attr_name), req).group(1)
            return True, value
        else:
            return False, None

    def process(self, file_path):
        """
        Function to process a file given its file path.
        """
        self.file_path = file_path
        self.get_requirements()

        self.errors = []
        for req in self.requirements:
            req_str = req["content"]
            _, id = self.check_exist_empty(req_str, "id")

            _, artifact_type = self.check_exist_empty(req_str, "artifact_type")
            if artifact_type == "Information":
                continue

            errors = []
            check_allocation = False
            for name in self.attr_names:
                is_filled, value = self.check_exist_empty(req_str, name)
                if is_filled == False:
                    errors.append(name)
                if name == "status" and value == "Accepted":
                    check_allocation = True
            if check_allocation:
                is_filled, value = self.check_exist_empty(req_str, "allocation")
                if not is_filled:
                    errors.append("allocation")
            if len(errors):
                self.errors.append({"id": id, "type": req["type"], "errors": errors})

        return len(self.errors) == 0

    def export_message(self):
        """
        Export error message if inconsistency found following this format:
        <Module path>
            <Requirement ID> - <Requirement Type>
                ERROR: field '<attribute name>' must be filled
        """
        if (self.errors is None) or len(self.errors) == 0:
            return ""
        message = self.file_path + "\n"
        for incorrect in self.errors:
            message += "\t{} - {}\n".format(str(incorrect["id"]), incorrect["type"])
            for attr_name in incorrect["errors"]:
                message += f"\t\tERROR: field '{attr_name}' must be filled\n"
        return message


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

    args = parser.parse_args()
    return args.inputs


if __name__ == "__main__":
    attribute_names = ["status", "crq", "verify", "safety_level"]

    requirements_dir = init_arguments()

    is_cons = True
    message = ""
    validator = RegExValidator(attribute_names)
    for f in os.listdir(requirements_dir):
        file_path = os.path.join(requirements_dir, f)
        if not validator.process(file_path):
            is_cons = False
        message += validator.export_message()

    if not is_cons:
        core.set_failed("\n" + message)
