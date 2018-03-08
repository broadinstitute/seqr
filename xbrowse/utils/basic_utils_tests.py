from django.test import TestCase
from xbrowse.utils.basic_utils import _encode_name, _decode_name


class BasicUtilsTest(TestCase):

    def test_encode_decode_name(self):

        # test special cases
        for test_string in [
            "SPECIAL_CHARS_TEST1_.,#*$[]{}()_1_.,#*$[]{}()/\\",
            "SPECIAL_CHARS_TEST2_..,,##**$$[[]]{{}}(())////\\\\",
            "SPECIAL_CHARS_TEST3__$dot$__$comma$__$hash$___$star$__$lp$__$rp$__$lsb$__$rsb$__$lcb$__$rcb$_",
            ".SPECIAL_START_CHAR",
            "*SPECIAL_START_CHAR",
            "__SPECIAL_START_CHAR",
            "__$SPECIAL_START_CHAR",
            "_$SPECIAL_START_CHAR",
        ]:

            decoded_test_string = _decode_name(_encode_name(test_string))
            self.assertEqual(test_string, decoded_test_string)

        # test all ascii chars
        for acii_code in range(32, 127):
            test_char = chr(acii_code)

            decoded_test_char = _decode_name(_encode_name(test_char))
            self.assertEqual(test_char, decoded_test_char)





