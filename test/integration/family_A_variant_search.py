#!/usr/bin/env python

import configargparse
import getpass
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
import sys

logging.basicConfig(format='%(asctime)-15s: %(message)s', level=logging.INFO, filename='create_subtasks.log', filemode='a')
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))


def log(message):
    """Utility func. for logging the given message (which can be any object)"""
    logger.info("---> " + str(message))


def url_get(wd, url):
    """Utility func. for opening the given url using the selenium webdriver object wd."""
    log("Open " + url)
    wd.get(url)
    log("     Opened")


def find_element(wd, by, value):
    """Utility func. for looking up and returning the given DOM element using the selenium webdriver object wd."""
    log("Finding elem by %s: %s" % (by, value))
    elem = wd.find_element(by, value)
    log("     Found elem by %s: %s" % (by, value))
    return elem


def find_elements(wd, by, value):
    """Utility func. for looking up and returning multiple DOM elements using the selenium webdriver object wd."""
    log("Finding elements by %s: %s" % (by, value))
    elements = wd.find_elements(by, value)
    log("     Found %s elements by %s: %s" % (len(elements), by, value))
    return elements


def submit_form(wd, id_value_map):
    """Assuming the currently-loaded web-page contains a form, this method
    types the given values into the form and submits it.

    Args:
        wd: selenium WebDriver object.
        id_id_value_map: dictionary that maps form element ids to their intended values
    """
    assert id_value_map, "id_value_map arg is empty: %s" % str(id_value_map)

    log("Filling out form with %s element(s)" % len(id_value_map))
    for elem_id, value in id_value_map.items():
        elem = find_element(wd, By.ID, elem_id)
        elem.send_keys(value)

    log("     Submitting..")
    elem.submit()


def run_test(wd, username=None):
    """This method implements the main test steps.

    Args:
        wd: a selenium WebDriver object.
        username: optional xBrowse username as a string. If provided, it will skip the username prompt.
    """
    wd.implicitly_wait(5)     # wait up to this many seconds for pages to load

    log("Signing in to xBrowse")
    if username is None:
        username = raw_input("Your xBrowse username: " )

    log("Your xBrowse username: %s" % username)
    passwd = getpass.getpass("Your xBrowse password: ")

    # sign in to project id page
    url_get(wd, "https://xbrowse.broadinstitute.org/login")
    elem = find_element(wd, By.XPATH, "//button[contains(@type, 'submit')]")
    elem.click()

    submit_form(wd, {"id_username_or_email": username, "id_password": passwd})

    # click on INMR_v9 project, and then click through to variant search
    elem = find_element(wd, By.XPATH, "//a[contains(@href, '/project/INMR_v9')]")
    elem.click()
    
    elem = find_element(wd, By.XPATH, "//a[contains(@href, '/project/INMR_v9/families')]")
    elem.click()
    
    elem = find_element(wd, By.XPATH, "//a[contains(@href, '/project/INMR_v9/family/A')]")
    elem.click()
    
    elem = find_element(wd, By.XPATH, "//a[contains(@href, '/project/INMR_v9/family/A/mendelian-variant-search')]")
    elem.click()

    # select inheritance mode
    elem = find_element(wd, By.XPATH, "//input[contains(@value, 'recessive')]")
    elem.click()

    # select incorrect func. annotation filter
    elem = find_element(wd, By.XPATH, "//input[@data-annot='essential_splice_site']")
    elem.click()
    elem = find_element(wd, By.XPATH, "//input[@data-annot='frameshift']")
    elem.click()
    elem = find_element(wd, By.ID, "run-search")
    elem.click()

    # THE CHECKS BELOW ASSUME NO OTHER FILTERS (eg. no allele frequency, genotype quality, etc.)
    
    # check that search results don't contain the variants
    xpos_list = []
    for elem in find_elements(wd, By.XPATH, "//a[@class='annotation-link' and boolean(@data-xpos)]"):
        xpos_list.append(elem.get_attribute('data-xpos'))
    
    expected_xpos_list = map(str, [1144873962, 1144915623, 1144917827, 1144923728, 3195505787, 3195505792, 6032551958, 7076240785, 
     7142099581, 7142099588, 7142099590, 7142099593, 7142223948, 7142223953, 12007045899, 12007045905])
    
    assert set(xpos_list) == set(expected_xpos_list), "Unexpected xpos list: %s\n doesn't match expected: %s" % (str(xpos_list), str(expected_xpos_list))
    assert len(xpos_list) == len(expected_xpos_list), "Unexpected xpos list length: %s" % str(xpos_list)

    import time
    time.sleep(10)

    # undo selections
    elem = find_element(wd, By.XPATH, "//input[@data-annot='essential_splice_site']")
    elem.click()
    elem = find_element(wd, By.XPATH, "//input[@data-annot='frameshift']")
    elem.click()

    # select correct functional annotation filters
    elem = find_element(wd, By.XPATH, "//input[@data-annot='nonsense']")
    elem.click()
    elem = find_element(wd, By.XPATH, "//a[@data-annot='inframe']")  # click the + to exand 'inframe' category
    elem.click()    
    elem = find_element(wd, By.XPATH, "//input[@data-annot='inframe_deletion']")
    elem.click()
    elem = find_element(wd, By.ID, "run-search")
    elem.click()


    # check that search results contain the variants
    xpos_list = []
    for elem in find_elements(wd, By.XPATH, "//a[@class='annotation-link' and boolean(@data-xpos)]"):
        xpos_list.append(elem.get_attribute('data-xpos'))
    
    expected_xpos_list = [u'1012854090', u'1012856105', u'3069168305', u'3069168400', u'6160211645', u'7142231625', u'11001016988', u'11001017466', u'11001017495', u'16024788422', u'22037964408']
    
    assert set(xpos_list) == set(expected_xpos_list), "Unexpected xpos list: %s\n doesn't match expected: %s" % (str(xpos_list), str(expected_xpos_list))
    assert len(xpos_list) == len(expected_xpos_list), "Unexpected xpos list length: %s" % str(xpos_list)


if __name__ == "__main__":
    p = configargparse.ArgParser(default_config_files=["~/.config_arg_parse"], 
                                 description="Test integration",
                                 add_config_file_help=False, 
                                 formatter_class=configargparse.ArgumentDefaultsRawHelpFormatter)

    p.add_argument("-u", "--username", help="xBrowse username")
    #p.add_argument("-p", "--project-id", help="project id")
    p.add_argument("-Q", "--quit", help="Quit the test browser instance after a successful test", action="store_true")

    g = p.add_mutually_exclusive_group()
    g.add_argument("--use-chrome", dest="browser", help="Run inside chrome", action="store_const", const="CHROME")
    g.add_argument("--use-firefox", dest="browser", help="Run inside chrome", action="store_const", const="FIREFOX")
    
    args = p.parse_args()

    if args.browser is None:
        wd = webdriver.Chrome()
    elif args.browser == "CHROME":
        wd = webdriver.Chrome()
    elif args.browser == "FIREFOX":
        wd = webdriver.Firefox()
    else:
        raise ValueError("Unexpected browser value: %s" % args.browser)

    log("-----------")
    run_test(wd, username=args.username)
    if args.quit:
        wd.quit()  # don't close the browser window so results can be inspected
