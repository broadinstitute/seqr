import re
from markdownify import markdownify as md
from seqr.models import Family as SeqrFamily, Individual as SeqrIndividual
from xbrowse_server.base.models import Family as BaseFamily, Individual as BaseIndividual

from django.core.management.base import BaseCommand



def strip(s, start_string, end_string):
    """Return s after replacing the 1st occurance of start_string until the last occurance of end_string with empty-string.
    If start_string or end_string not found, return the original input string s.

    This method is (surprisingly) necessary because re.sub('<!--.*-->', '', s, re.DOTALL) fails to match all cases (for example
    where there's unusual white-space that isn't matched by . even with re.DOTALL). 
    re.sub('<!--(.*[\W]*)*-->', '', s, re.DOTALL)  matches all cases, but runs into catastrophic backtracking / inifite loops
    in some cases.
    """
    while True:
        i1 = s.find(start_string)
        if i1 < 0:
            break
        i2 = s.find(end_string, i1+1)
        if i2 < 0:
            break
        s = s[:i1]+s[i2+len(end_string):]
    return s

def convert_to_markdown(s):
    """Converts an html string to markdown"""

    s = unicode(s).encode('utf-8')
    #s = ''.join([i if ord(i) < 128 else ' ' for i in s])
    #print("Original:\n" + s)
    #print("====")

    s = strip(s, '[if', 'endif]')
    s = strip(s, '<!--', '-->')
    s = s.replace('<div>', "<br /><div>")
    s = s.replace('<tr>', "<br /><tr>")
    s = s.replace('<ul>', "<br /><ul>")
    s = s.replace('<li>', "<br /><li>")
    s = md(s).encode('utf-8')
    s = s.strip('"')
    s = s.strip()

    return s

class Command(BaseCommand):

    def handle(self, *args, **options):

        # Individual fields
        for attr in ['case_review_discussion', 'notes']:
            print("====================")
            print(attr)
            print("====================")
            for i in SeqrIndividual.objects.all():
                if not getattr(i, attr):
                    continue

                s = getattr(i, attr)
                #print("-----------------------")
                #print(s)

                s = convert_to_markdown(s)
                setattr(i, attr, s)
                i.save()

        # Family fields
        for attr in ['analysis_notes', 'description', 'analysis_summary', 'internal_case_review_notes', 'internal_case_review_summary']:
            print("====================")
            print(attr)
            print("====================")
            for f in SeqrFamily.objects.all():
                if not getattr(f, attr):
                    continue

                s = getattr(f, attr)
                #print("-----------------------")
                #print(s)

                s = convert_to_markdown(s)
                setattr(f, attr, s)
                f.save()
                
                if attr == "analysis_notes":
                    base_attr = "about_family_content"
                elif attr == "description":
                    base_attr = "short_description"
                elif attr == "analysis_summary":
                    base_attr = "analysis_summary_content"
                elif attr == "internal_case_review_notes":
                    base_attr = "internal_case_review_notes"
                elif attr == "internal_case_review_summary":
                    base_attr = "internal_case_review_summary"
                else:
                    raise ValueError(attr)
                try:
                    base_f = BaseFamily.objects.get(family_id=f.family_id, project__project_id = f.project.deprecated_project_id)
                except Exception as e:
                    print(e)
                    print(f.project.deprecated_project_id, f.family_id)
                    continue
                
                setattr(base_f, base_attr, s)
                base_f.save()
