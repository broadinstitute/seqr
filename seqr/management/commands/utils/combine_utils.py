import json
import logging

logger = logging.getLogger(__name__)


def choose_one(model, field_name, value_a, value_b, default_value=None, use_lower_value=False, use_higher_value=False, verbose=True):
    """Logic for allowing users to select which of two conflicting values to keep during a merge.
    Args:
        model: django model object
        field_name (string): name of model field that's being merged
        value_a: one choice for field's value
        value_b: the other choice for the field's value
        default_value: (optional) default value for this field. If provided, then value_a or value_b
            can be automatically selected when one version is the default value.
        use_lower_value (bool): if True, and both values are set, the smaller value is returned.
        use_higher_value (bool): if True, and both values are set, the larger value is returned.
        verbose (bool): if True, the returned value will be printed.

    Returns:
         either value_a or value_b depending on which one is set to a non-empty or non-default value.
         If both are set, the user must manually select whether to use value_a or value_b
    """
    def print_out(value):
        if verbose:
            print("Set %s.%s to %s" % (type(model).__name__, field_name, ('"%s"' % unicode(value).encode('UTF-8')) if isinstance(value, (str, unicode)) else value))

    # generic cases
    if value_a == value_b:
        print_out(value_a)
        return value_a

    if not value_a:
        print_out(value_b)
        return value_b
    if not value_b:
        print_out(value_a)
        return value_a

    if value_a == default_value:
        print_out(value_b)
        return value_b
    if value_b == default_value:
        print_out(value_a)
        return value_a

    if use_lower_value:
        print_out(min(value_a, value_b))
        return min(value_a, value_b)
    if use_higher_value:
        print_out(max(value_a, value_b))
        return max(value_a, value_b)

    # special cases
    if field_name in ["maternal_id", "paternal_id"]:
        if value_a in [".", ""]:
            print_out(value_b)
            return value_b
        if value_b in [".", ""]:
            print_out(value_a)
            return value_a

    if field_name == "phenotips_data":
        # TODO merge phenotips json
        value_a_json = json.loads(value_a)
        value_b_json = json.loads(value_b)
        #print("value_a has %s features" % len(value_a_json.get('feature', [])))
        #print("value_b has %s features" % len(value_b_json.get('feature', [])))
        if len(value_a) > len(value_b):
            print_out(value_a)
            return value_a
        if len(value_b) > len(value_a):
            print_out(value_b)
            return value_b

    # let user decide
    print("\r===================")
    while True:
        i = raw_input((
                          "select %s.%s (enter a or b, or "
                          "e to edit, or "
                          "cs to concatenate with space in between, or cn to concatenate with new line):\n"
                          "   a: %s\n"
                          "   b: %s\n"
                          "[a/b/e/cs/cn]: ") % (model, field_name, value_a, value_b))
        i = i.strip()
        if i == 'a':
            result = value_a
        elif i == 'b':
            result = value_b
        elif i == 'e':
            result = raw_input("Enter new value: ")
            result = result.strip()
        elif i == 'cs' or i == 'cn':
            result = "%s%s%s" % (value_a, ' ' if i == 'cs' else '\n', value_b)
        else:
            continue

        print_out(value_a)
        return result


def ask_yes_no_question(question):
    """Prompts the user and then returns True or False depneding on whether the user replied 'Y' or 'n'"""
    while True:
        i = raw_input(str(question) + " [Y/n] ")

        if i and i.lower() == 'y':
            return True
        elif i and i.lower() == 'n':
            return False