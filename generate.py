#!/usr/bin/env python

import re
import os
import rstr
import sys
import yaml
import glob
import json
import random

def gen_param(id, param):
    if 'enum' in param:
        return random.choice(param['enum'])
    elif 'type' in param:
        if param['type'] == "boolean":
            return random.choice([True, False])
        elif param['type'] == "string":
            if 'pattern' in param:
                return rstr.xeger(param['pattern'])
            print("Not found %s" % (param))
            return ""
    print("Not found %s %s" % (id, param))
    return None

def gen_config_param(config):
    if config["method"] == "randint":
        return random.randint(*config["args"])
    if config["method"] == "randfloat":
        args = config["args"]
        return (random.random() * args[1] - args[0]) + args[0]
    if config["method"] == "generate":
        args = config["args"]
        return rstr.xeger(args[0])
    return None

def gen_record(id, schema_map, file_map, config):
    schema_config = config["generate"][id]
    out = {}
    path = schema_map[config["generate"][id]["schema"]]
    props = file_map[path]['properties']
    props_config = config["generate"][id]["properties"]

    for k, v in props.items():
        if '$ref' in v:
            tmp = v['$ref'].split("#")
            if tmp[0] in file_map:
                nid = re.sub(r'^\/', '', tmp[1])
                if nid in file_map[tmp[0]]:
                    param = file_map[tmp[0]][nid]
                    out[k] = gen_param(k, param)
        elif k in props_config:
            out[k] = gen_config_param(props_config[k])
        else:
            out[k] = gen_param(k, v)
    return out


if __name__ == "__main__":

    config_path = sys.argv[1]
    with open(config_path) as handle:
        config = yaml.load(handle.read())

    schema_dir = sys.argv[2]
    # Load in the files used to describe the schema
    schema_map = {}
    file_map = {}
    for y in glob.glob(os.path.join(schema_dir, "*.yaml")):
        with open(y) as handle:
            data = yaml.load(handle.read())
        fname = os.path.basename(y)
        file_map[fname] = data
        if data.get("$schema", "") == "http://json-schema.org/draft-04/schema#":
            schema_map[data['id']] = fname

    for name, rec in config['generate'].items():
        with open(rec['file'], "w") as ohandle:
            for i in range(rec["count"]):
                d = gen_record(name, schema_map, file_map, config)
                ohandle.write(json.dumps(d))
                ohandle.write("\n")
