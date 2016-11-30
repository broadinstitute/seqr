import os

def build_hpo_dict():
    with open("hp.obo",'r') as f:
        lines = f.readlines()
        current_id = None
        current_is_a = None
        hpo_dict = {}
        current_is_a_tuple = ()
        for line in lines:
            if line.startswith("id:"):
                current_id = line.strip().split("id:")
                current_id = current_id[1].strip()
            elif line.startswith("is_a:"):
                current_is_a = line.strip().split("is_a:")
                current_is_a = current_is_a[1]
                b = current_is_a.split("!")
                current_is_a_tuple = (b[0].strip(),b[1].strip())
            if current_id is not None:
                hpo_dict[current_id]=current_is_a_tuple
        print hpo_dict
        return hpo_dict

build_hpo_dict()
