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
            print("Not found %s %s" % (id, param))
            return ""
    print("Not found %s %s" % (id, param))
    return None

def gen_random(config, kwds=None):
    args = config['args']
    if not isinstance(args, list):
        args = [args]
    if config["method"] == "randint":
        return random.randint(*args)
    if config["method"] == "randfloat":
        return (random.random() * args[1] - args[0]) + args[0]
    if config["method"] == "generate":
        return rstr.xeger(args[0])
    if config["method"] == "template":
        return args[0].format(**kwds)
    if config["method"] == "template-loop":
        out = []
        for i in args[0]:
            out.append(args[1].format(arg=i, **kwds))
        return out
    return None

def gen_record(id, schema_map, file_map, config, variables):
    schema_config = config["outputs"][id]
    out = {}
    path = schema_map[config["outputs"][id]["schema"]]
    props = file_map[path]['properties']
    props_config = config["outputs"][id]["properties"]

    for k, v in props.items():
        if '$ref' in v:
            tmp = v['$ref'].split("#")
            if tmp[0] in file_map:
                nid = re.sub(r'^\/', '', tmp[1])
                if nid in file_map[tmp[0]]:
                    param = file_map[tmp[0]][nid]
                    out[k] = gen_param(k, param)
        elif k in props_config:
            out[k] = gen_random(props_config[k], variables)
        else:
            out[k] = gen_param(k, v)
    return out

class IDTables:

    def __init__(self, config):
        self.table_parent = {}
        self.tables = {}
        # generate parent id tables
        for name, tab in config.get("tables", {}).items():
            if 'count' in tab:
                o = {}
                for i in range(tab['count']):
                    o[gen_random(tab)] = None
                self.tables[name] = o
                self.table_parent[name] = None


        # generate child id tables
        added = True
        while added:
            added = False
            for name, tab in config.get("tables", {}).items():
                if name not in self.tables and 'link' in tab and tab['link'] in self.tables:
                    added = True
                    o = {}
                    for s in self.tables[tab['link']]:
                        n = gen_random(tab, {tab['link']:s})
                        if isinstance(n, list):
                            for i in n:
                                o[i] = s
                        else:
                            o[n] = s
                    self.tables[name] = o
                    self.table_parent[name] = tab['link']

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

    idtables = IDTables(config)

    for name, rec in config['outputs'].items():
        with open(rec['file'], "w") as ohandle:
            if "count" in rec:
                for i in range(rec["count"]):
                    d = gen_record(name, schema_map, file_map, config, {})
                    ohandle.write(json.dumps(d))
                    ohandle.write("\n")
            elif "id_table" in rec:
                for i in idtables.tables[rec['id_table']]:
                    d = gen_record(name, schema_map, file_map, config, {"id" : i})
                    ohandle.write(json.dumps(d))
                    ohandle.write("\n")
