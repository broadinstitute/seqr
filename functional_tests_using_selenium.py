import time
import unittest

from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


#
# User can modify these
#

LIVE_SERVER_URL = 'http://localhost:8009'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'


def wait_for_xpath(selenium, xpath, duration=10):
    """
    Keep searching for xpath until it exists; return when it does
    """
    poll_interval = 0.1

    total_sleep = 0
    while total_sleep <= duration:
        time.sleep(poll_interval)
        total_sleep += poll_interval

        try:
            e = selenium.find_element_by_xpath(xpath)
            return e
        except NoSuchElementException:
            pass


def choose_select(selenium, xpath_of_select, value):
    """
    Wrapper for choosing select box by value
    """
    el = selenium.find_element_by_xpath(xpath_of_select)
    for option in el.find_elements_by_tag_name('option'):
        if option.get_attribute('value') == value:
            option.click()
            return
    for optgroup in el.find_elements_by_tag_name('optgroup'):
        for option in optgroup.find_elements_by_tag_name('optgroup'):
            if option.get_attribute('value') == value:
                option.click()
                return


def set_freq_to_10(selenium):
    """
    Set the frequency slider to 10%
    """
    ac = ActionChains(selenium)
    el = selenium.find_element_by_xpath('//a[@class="ui-slider-handle ui-state-default ui-corner-all"]')
    ac.move_to_element(el)
    ac.click_and_hold()
    ac.move_by_offset(80, 0)
    ac.release()
    ac.perform()


class BasicViewTests(unittest.TestCase):
    """
    Just visit all the views and make sure they look okay
    """

    def setUp(self):

        self.selenium = WebDriver()
        self.live_server_url = LIVE_SERVER_URL

        # login boilerplate blah
        self.selenium.get(self.live_server_url + '/login')
        username_input = self.selenium.find_element_by_name("username_or_email")
        username_input.send_keys(ADMIN_USERNAME)
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys(ADMIN_PASSWORD)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()

    def test_home(self):

        self.selenium.get(self.live_server_url + '/')

        # two project links are there
        self.selenium.find_element_by_link_text('1000 Genomes')

    def test_project_home(self):

        self.selenium.get(self.live_server_url + '/project/1kg')

    def test_family_home(self):

        self.selenium.get(self.live_server_url + '/project/1kg/family/HG1')

    def tearDown(self):
        self.selenium.quit()


class FamilyBrowseTests(unittest.TestCase):
    """
    Test all the different views you can go to on the family test page
    """
    def setUp(self):

        self.selenium = WebDriver()
        self.live_server_url = LIVE_SERVER_URL

        # login boilerplate blah
        self.selenium.get(self.live_server_url + '/login')
        username_input = self.selenium.find_element_by_name("username_or_email")
        username_input.send_keys(ADMIN_USERNAME)
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys(ADMIN_PASSWORD)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()

        # visit the family browse page
        self.selenium.get(self.live_server_url + '/project/1kg/family/1/mendelian-variant-search')

    def test_recessive_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="recessive"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("7 variants" in stats_content)

    def test_homozygous_recessive_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="homozygous_recessive"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("1 variants" in stats_content)

    def test_x_linked_recessive_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="x_linked_recessive"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("No variants" in stats_content)

    def test_compound_het_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="compound_het"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("6 variants" in stats_content)

    def test_dominant_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="dominant"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("21 variants" in stats_content)

    def test_de_novo_basic(self):

        self.selenium.find_element_by_xpath('//input[@name="standard_inheritance"][@value="de_novo"]').click()
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("6 variants" in stats_content)

    def test_custom_inheritance(self):
        self.selenium.find_element_by_xpath('//li[@class="inheritance-pill-li"][@data-search_mode="custom_inheritance"]/a').click()
        time.sleep(.5)
        choose_select(self.selenium, '//select[@class="col-md-2 select-genotype form-control"][@data-indiv_id="NA19675"]', 'alt_alt')
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("21 variants" in stats_content)

    def tearDown(self):
        self.selenium.quit()


# class CohortVariantSearch(unittest.TestCase):
#     """
#     """
#     def setUp(self):
#
#         self.selenium = WebDriver()
#         self.live_server_url = LIVE_SERVER_URL
#
#         # login boilerplate blah
#         self.selenium.get(self.live_server_url + '/login')
#         username_input = self.selenium.find_element_by_name("username_or_email")
#         username_input.send_keys('bt')
#         password_input = self.selenium.find_element_by_name("password")
#         password_input.send_keys('bt')
#         self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
#
#         # visit the family browse page
#         self.selenium.get(self.live_server_url + '/project/g1k/cohort/random_cohort/variant-search')
#
#     def test_single_homalt(self):
#
#         time.sleep(.3)
#         choose_select(self.selenium, '//select[@data-indiv_id="HG00552_1"]', 'alt_alt')
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'high_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         stats_content = self.selenium.find_element_by_id('variant-stats-container').text
#         self.assertTrue("20 variants" in stats_content)
#
#     def tearDown(self):
#         self.selenium.quit()


class FamilyBrowseVariantFilterTests(unittest.TestCase):
    """
    Test the same recessive search with the more granular variant filters
    """
    def setUp(self):

        self.selenium = WebDriver()
        self.live_server_url = LIVE_SERVER_URL

        # login boilerplate blah
        self.selenium.get(self.live_server_url + '/login')
        username_input = self.selenium.find_element_by_name("username_or_email")
        username_input.send_keys(ADMIN_USERNAME)
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys(ADMIN_PASSWORD)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()

        # visit the family browse page
        self.selenium.get(self.live_server_url + '/project/1kg/family/1/mendelian-variant-search')

        # set inheritance
        self.selenium.find_element_by_xpath('//li[@class="inheritance-pill-li"][@data-search_mode="all_variants"]/a').click()

    def test_genes_filter(self):

        self.selenium.find_element_by_xpath('//a[@href="#collapse-region"]').click()
        time.sleep(.4)
        genes_input = self.selenium.find_element_by_id("region-genes")
        genes_input.send_keys('cdcp2\nmpv17')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("9 variants" in stats_content)

    def test_region_filter(self):

        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')

        self.selenium.find_element_by_xpath('//a[@href="#collapse-region"]').click()
        time.sleep(.4)
        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        genes_input = self.selenium.find_element_by_id("region-coords")
        genes_input.send_keys('chr6:31000000-33000000')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("8 variants" in stats_content)

    def test_region_filter_full_chr(self):

        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')

        self.selenium.find_element_by_xpath('//a[@href="#collapse-region"]').click()
        time.sleep(.4)

        choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
        genes_input = self.selenium.find_element_by_id("region-coords")
        genes_input.send_keys('chr6')

        self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
        wait_for_xpath(self.selenium, '//div[@id="summary-container"]')

        stats_content = self.selenium.find_element_by_id('variant-stats-container').text
        self.assertTrue("92 variants" in stats_content)

    def tearDown(self):
        self.selenium.quit()

# class CohortGeneSearchTests(unittest.TestCase):
#     """
#     Test all the different views you can go to on the cohort browse page
#     """
#     def setUp(self):
#
#         #self.selenium = webdriver.Chrome()
#         self.selenium = WebDriver()
#         self.live_server_url = 'http://localhost:8000'
#
#         # login boilerplate blah
#         self.selenium.get(self.live_server_url + '/login')
#         username_input = self.selenium.find_element_by_name("username_or_email")
#         username_input.send_keys('bt')
#         password_input = self.selenium.find_element_by_name("password")
#         password_input.send_keys('bt')
#         self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
#
#         # visit the cohort browse page
#         self.selenium.get(self.live_server_url + '/project/g1k/cohort/random_cohort/cohort-gene-search')
#
#     def test_recessive_basic(self):
#         self.selenium.find_element_by_xpath('//input[@name="cohort_inheritance"][@value="recessive"]').click()
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         results_content = self.selenium.find_element_by_id('resultsContainer').text
#         self.assertTrue("Returned 60 genes" in results_content)
#
#     def test_homozygous_recessive_basic(self):
#
#         self.selenium.find_element_by_xpath('//input[@name="cohort_inheritance"][@value="homozygous_recessive"]').click()
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         results_content = self.selenium.find_element_by_id('resultsContainer').text
#         self.assertTrue("Returned 53 genes" in results_content)
#
#     def test_x_linked_recessive_basic(self):
#
#         self.selenium.find_element_by_xpath('//input[@name="cohort_inheritance"][@value="x_linked_recessive"]').click()
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         results_content = self.selenium.find_element_by_id('resultsContainer').text
#         self.assertTrue("Returned 2 genes" in results_content)
#
#     def test_compound_het_basic(self):
#
#         self.selenium.find_element_by_xpath('//input[@name="cohort_inheritance"][@value="compound_het"]').click()
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'moderate_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         results_content = self.selenium.find_element_by_id('resultsContainer').text
#         self.assertTrue("Returned 6 genes" in results_content)
#
#     def test_dominant_basic(self):
#
#         self.selenium.find_element_by_xpath('//input[@name="cohort_inheritance"][@value="dominant"]').click()
#         choose_select(self.selenium, '//select[@id="variant-presets-select"]', 'high_impact')
#         choose_select(self.selenium, '//select[@id="quality-defaults-select"]', 'high_quality')
#
#         self.selenium.find_element_by_xpath('//a[@id="run-search"]').click()
#         wait_for_xpath(self.selenium, '//div[@id="summary-container"]')
#
#         results_content = self.selenium.find_element_by_id('resultsContainer').text
#         self.assertTrue("Returned 6 genes" in results_content)

    def tearDown(self):
        self.selenium.quit()

if __name__ == '__main__':
    unittest.main()