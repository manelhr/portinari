# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
#                                     # / ---------------------------- \ #                                             #
#                                     # | AUTHOR: MANOEL HORTA RIBEIRO | #                                             #
#                                     # \ ---------------------------- / #                                             #
#                                                                                                                      #
# This script does the whole preprocessing of the two files. Basically it:                                             #
#                                                                                                                      #
#                   - Fill empty attributes as specified by the config file.                                           #
#                   * Uses the mandatory "nan" field on the config file.                                               #
#                                                                                                                      #
#                   - Does the conversion from date string to int as specified by config file.                         #
#                   * Uses the optional "conversion" field on each attribute & the mandatory "timeformat" attribute.   #
#                                                                                                                      #
#                   - Drop columns and invalid rows as specified by the config file.                                   #
#                   * Uses the optional field "drop_col" and "drop_val" on each attribute                              #
#                                                                                                                      #
#                   - Rename the categorical values of some attrs as specified by config file. Must be numbers wo 0.   #
#                   * Uses the optional "rename":{"old":"new",...} field on each attribute.                            #
#                                                                                                                      #
#                   - Remove trailing zeroes in all attrbutes, just to prevent having 1.0 as float                     #
#                                                                                                                      #
#                   - Creates two attributes "age" and "sincelast", derived from "eventdate" and "entitycreation".     #
#                   * Uses the mandatory "eventdate" & "entitycreation" fields on config file.                         #
#                                                                                                                      #
#                   -  Make all rows numeric (either float or int, no strings allowed).                                #
#                                                                                                                      #
#                   -  Make relational-like tables.                                                                    #
#                   * Uses the mandatory "default" field and the optional "entity" and "event" fields on each attr.    #
#                                                                                                                      #
#  The config file contains the following fields:                                                                      #
# {                                                                                                                    #
#  "variables" : // if variables are not specified they will be treated according to default configurations.           #
#  {                                                                                                                   #
#    (name_in_row): {                                                                                                  #
#                     "new_name": string w/ name the attribute will have in the new datafile, MBD unless dropcol=true, #
#                     "renaming": hash containing ´old_categorical_val´ : ´new_categorical_val´, OPTIONAL,             #
#                     "event"/"entity": (true|false) specified destination tables, if not defined, defined by standard,#
#                     "drop_val": list containing attributes values not allowed, OPTIONAL,                             #
#                     "drop_col": (true|false) list w/ attr to drop, if true, should be the only value, OPTIONAL,      #
#                     "conversion": (to_sec|to_min|to_hour|to_day|to_week|to_month|to_year), OPTIONAL                  #
#                    }                                                                                                 #
#      ...                                                                                                             #
# }                                                                                                                    #
#                                                                                                                      #
#  "id": name of id attribute in dataset, MBD,                                                                         #
#  "eventdate": name of eventdate attribute in current dataset, MBD,                                                   #
#  "entitycreation": name of eventcreation attribute in curr dataset, MBD,                                             #
#                                                                                                                      #
#  "time_format": (%d.%m.%Y|...) format of the dates in the original dataset, MBD,                                     #
#  "nan": value for non defined values in new dataset, MBD,                                                            #
#  "default": (event|entity) default table where undescribed variables go, MBD,                                        #
#                                                                                                                      #
#  "sincelast": name of sincelast attribute in future dataset, MBD,                                                    #
#  "age": name of age attribute in future dataset, MBD,                                                                #
#  "age_conversion": conversion of age attribute, MBD,                                                                 #
#                                                                                                                      #
#  "directory": path to directory where the data is, MBD,                                                              #
#  "name": name of the file, MBD,                                                                                      #
# }                                                                                                                    #
#                                                                                                                      #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #


import numpy as np
import functools
import datetime
import pandas
import pickle
import json
import time
import os

# ---- Helpers ----


def bool_drop(default, table, event, entity):
    if event == "nothing" and entity == "nothing":
        if table == "entity" and default == "event":
            return True
        if table == "event" and default == "entity":
            return True
    if event == "true" and entity != "true" and table == "entity":
        return True
    if event != "true" and entity == "true" and table == "event":
        return True
    return False


def drop_cols(default, table_type, var, all_a, age="", sincelast=""):
    to_drop = []
    names = []
    for col in var:
        if "drop_col" in var[col] and var[col]["drop_col"] == "true":
            continue
        entity, event = "nothing", "nothing"
        if "new_name" in var[col]:
            names.append(var[col]["new_name"])
        if "entity" in var[col] and var[col]["entity"] == "true":
            entity = "true"
        if "event" in var[col] and var[col]["event"] == "true":
            event = "true"

        if bool_drop(default, table_type, event, entity):
            to_drop.append(var[col]["new_name"])

    for col in all_a:
        if col not in names and col not in [age, sincelast]:
            if default == "entity" and table_type == "event":
                to_drop.append(col)
            elif default == "event" and table_type == "entity":
                to_drop.append(col)

        if col in [age, sincelast] and table_type == "entity":
            to_drop.append(col)

    return to_drop


def time_flags(flag):
    if flag == "to_sec":
        ms = 1
    elif flag == "to_min":
        ms = 60
    elif flag == "to_hour":
        ms = 3600
    elif flag == "to_day":
        ms = 86400
    elif flag == "to_week":
        ms = 604800
    elif flag == "to_month":
        ms = 2628000
    elif flag == "to_year":
        ms = 31536000
    return ms


def unapply_time_flag(st, flag, config):
    ms = time_flags(flag)

    if st == config["nan"]:
        return st
    else:
        return ms * st


def apply_time_flag(st, flag, config):
    ms = time_flags(flag)

    if st == config["nan"]:
        return st
    else:
        return int(st / ms)


def to_unix(st, flag, config):
    if st != config["nan"]:
        st = np.floor(int(time.mktime(datetime.datetime.strptime(st, config["time_format"]).timetuple())))

    return apply_time_flag(st, flag, config)


# all together in nice way


def drop_row_cols(df, config):
    for key, var in config["variables"].items():
        # Drop Columns
        if "drop_col" in var and var["drop_col"] == "true":
            del df[key]
        elif "drop_val" in var:
            df = df[~df[key].isin(var["drop_val"])]

    return df


def fill_na(df, config):
    return df.fillna(config["nan"])


def time_conversion(df, config):
    for key, var in config["variables"].items():
        if "conversion" in var:
            f = functools.partial(to_unix, flag=var["conversion"], config=config)
            df[key] = df[key].apply(f)

    return df


def rename(df, config):
    for i in config["variables"]:
        if "renaming" in config["variables"][i]:
            loc = list(df.columns.values).index(i)
            table = df.values
            for row in range(len(table)):
                type_c = type(table[row][loc])
                table[row][loc] = type_c(config["variables"][i]["renaming"][str(table[row][loc])])
            df = pandas.DataFrame(table, columns=df.columns)

        if "new_name" in config["variables"][i]:
            df.rename(columns={i: config["variables"][i]["new_name"]}, inplace=True)

    return df


def remove_trailing_zeroes(df, config):
    table = df.values
    for row in range(len(table)):
        for col in range(len(table[row])):
            val = table[row][col]
            if type(val) == str and len(val) >= 3 and val[-2:] == ".0":
                table[row][col] = val[:-2]

    return pandas.DataFrame(table, columns=df.columns)


def calculate_age(df, config):
    name_eventdate = config["variables"][config["eventdate"]]["new_name"]
    f_eventdate = functools.partial(unapply_time_flag,
                                    flag=config["variables"][config["eventdate"]]["conversion"],
                                    config=config)

    name_entitycreation = config["variables"][config["entitycreation"]]["new_name"]
    f_entitycreation = functools.partial(unapply_time_flag,
                                         flag=config["variables"][config["entitycreation"]]["conversion"],
                                         config=config)

    df[config["age"]] = df[name_eventdate].apply(f_eventdate) - df[name_entitycreation].apply(f_entitycreation)

    f_age = functools.partial(apply_time_flag, flag=config["age_conversion"], config=config)

    df[config["age"]] = df[config["age"]].apply(f_age)

    return df


def calculate_sincelast(df, config):
    name_id = config["variables"][config["id"]]["new_name"]
    name_eventdate = config["variables"][config["eventdate"]]["new_name"]

    df[config["sincelast"]] = df[name_eventdate].values - np.array([0] + list(df[name_eventdate].values[:-1]))

    loc_id = list(df.columns.values).index(name_id)
    loc_sl = list(df.columns.values).index(config["sincelast"])

    previous = None
    table = df.values
    for row in range(len(table)):

        if table[row][loc_id] != previous:
            table[row][loc_sl] = 0
            previous = table[row][loc_id]

    return pandas.DataFrame(table, columns=df.columns)


def make_numeric(df):
    for col in df.columns:
        df[col] = pandas.to_numeric(df[col])
    return df

def make_tables(df, config):
    df_entity = df.drop(drop_cols(config["default"],
                                  "entity",
                                  config["variables"],
                                  df.columns,
                                  age=config["age"],
                                  sincelast=config["sincelast"]), axis=1)

    df_events = df.drop(drop_cols(config["default"],
                                  "event",
                                  config["variables"],
                                  df.columns,
                                  age=config["age"],
                                  sincelast=config["sincelast"]), axis=1)

    return df_entity, df_events


def make_all(config):
    raw_dir = config["directory"]
    name = config["name"]

    # paths
    df = pandas.read_csv(raw_dir + name, dtype=object, na_values=" ")

    # fill na
    df = fill_na(df=df, config=config)

    # drop rows and cols
    df = drop_row_cols(df=df, config=config)

    # time conversion
    df = time_conversion(df=df, config=config)

    # rename values and columns
    df = rename(df=df, config=config)

    # remove trailing zeroes
    df = remove_trailing_zeroes(df=df, config=config)

    # calculate age
    df = calculate_age(df=df, config=config)

    # calculate sincelast
    df = calculate_sincelast(df=df, config=config)

    # make all rows numeric
    df = make_numeric(df=df)

    # make tables
    df_entity, df_event = make_tables(df=df, config=config)

    # dumps pickle object
    filename, file_ext = os.path.splitext(raw_dir + name)
    pickle.dump(df_entity, open(filename + "_entity", "wb"))
    pickle.dump(df_event, open(filename + "_event", "wb"))


if __name__ == "__main__":
    mixed_config = json.loads(open("./data/surveys/meta/surveyboth_export.json", "r").read())
    make_all(mixed_config)
