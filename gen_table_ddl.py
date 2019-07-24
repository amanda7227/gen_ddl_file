import cx_Oracle
import datetime
import os
import subprocess
import sys
from subprocess import Popen, PIPE

gen_table_root_folder = os.path.dirname(os.path.realpath(__file__)) + "\\"
gen_table_source_folder = os.path.dirname(os.path.realpath(__file__)) + "\\table_source_file\\"
gen_table_target_folder = os.path.dirname(os.path.realpath(__file__)) + "\\table_target_file\\"
dt_today = str(datetime.date.today())
enter_str = "\n"
g_svn_author = ""
g_con_phr_citizen = ""
g_svn_issue = ""
g_svn_file_header = ""
g_svn_file_footer = ""
TABLE_NAME_ABB = ""
table_name_abb_list = []
g_list_ddl_files = []
g_table_lists = []


class AllDDLFile:
    def __init__(self):
        self.tab_name = ""
        self.fk_name = []
        self.idx_name = []
        self.cns_name = []


def load_config_file():
    global g_svn_author
    global g_con_phr_citizen
    global g_svn_issue
    with open(gen_table_root_folder + "config.txt") as of:
        for of_line in of:
            config_line = of_line.split("=")
            if config_line[0] == "AUTHOR":
                g_svn_author = config_line[1].strip()
            elif config_line[0] == "JIRA_ISSUE":
                g_svn_issue = config_line[1].strip()
            elif config_line[0] == "CON_ALERT_PHR_CITIZEN":
                g_con_phr_citizen = config_line[1].strip()


def load_order_file():
    global g_table_lists
    with open(gen_table_root_folder + "order.txt") as of:
        for of_line in of:
            g_table_lists.append(of_line.strip().upper())


print("g_svn_author=" + g_svn_author + ",g_svn_issue=" + g_svn_issue + ",g_con_phr_citizen=" + g_con_phr_citizen)
load_config_file()
g_svn_file_header = "-- CHANGED BY: " + g_svn_author + enter_str + "-- CHANGE DATE: " + dt_today + enter_str + "-- CHANGE REASON: " + g_svn_issue + enter_str
print("g_svn_author=" + g_svn_author + ",g_svn_issue=" + g_svn_issue + ",g_con_phr_citizen=" + g_con_phr_citizen)
g_svn_file_footer = "-- CHANGE END: " + g_svn_author
con = cx_Oracle.connect(g_con_phr_citizen)
# All change table
table_lists = []

for root, dirs, files in os.walk(gen_table_source_folder):
    for filename in files:
        # print(filename)
        table_lists.append(filename.strip().upper().replace(".TXT", ""))
load_order_file()
# for file_name in table_lists:
for file_name in g_table_lists:
    p_key_list = []
    TABLE_NAME_ABB = file_name[0:3]
    i_abb_index = 1
    while any(TABLE_NAME_ABB in s for s in table_name_abb_list):
        TABLE_NAME_ABB = file_name[i_abb_index:i_abb_index + 3]
        i_abb_index = i_abb_index + 1

    table_name_abb_list.append(TABLE_NAME_ABB)

    with open(gen_table_source_folder + file_name + ".TXT") as fp:
        all_ddl_file = AllDDLFile()
        all_ddl_file.tab_name = file_name + ".tab"
        cnt = 1
        date = str(datetime.date.today())
        ddl = g_svn_file_header + "Create table " + file_name + enter_str + "("
        ddl_comment = "-- Add comments to the table" + enter_str + "COMMENT ON TABLE " + file_name + " IS "

        all_table = []
        space_long = 0
        forign_key = []
        check_key = []
        idx_key = []
        # Get longst parameter
        for line in fp:
            # print("Line {}: {}".format(cnt, line.strip()))
            table_column = line.split("|")
            if space_long < len(table_column[0]) and cnt > 1:
                space_long = len(table_column[0])
            # print(table_column)
            all_table.append(table_column)
            cnt = cnt + 1

        # print(all_table)
        cnt = 1
        for line in all_table:
            # print("Line {}: {}".format(cnt, line.strip()))
            # table_column = line.split("|")
            # print(table_column)
            # print(line)
            if cnt < 2:
                cnt = cnt + 1
                continue
            if cnt >= 2:
                ddl = ddl + enter_str

            table_column_0 = line[0].strip().upper()
            ddl = ddl + table_column_0

            table_column_1 = line[1].upper()
            # print(str(space_long))
            # print(len(line[0]))
            # print(table_column_1)
            if table_column_0.find("FLG_") >= 0:
                ddl_chk = "ALTER TABLE " + file_name + " add CONSTRAINT " + TABLE_NAME_ABB + "_" + line[
                    0] + "_CHK CHECK(" + line[0] + " IN ('Y','N'));" + enter_str
                # Generate check key ddl
                ddl_check_name = TABLE_NAME_ABB + "_" + line[0] + "_CHK"
                fo_check = open(gen_table_target_folder + ddl_check_name.upper() + ".cns", "w")
                # print("文件名为: ", fo_check.name)
                ddl_chk = g_svn_file_header + ddl_chk + g_svn_file_footer
                fo_check.write(ddl_chk)
                fo_check.close()
                check_key.append(ddl_check_name.upper() + ".cns")

            real_space = (space_long + 1) - len(table_column_0)
            if table_column_1 == "VARCHAR":
                ddl = ddl + real_space * " " + "VARCHAR2(" + line[2].zfill(3) + " CHAR)"
            elif table_column_1 == "NUMBER":
                ddl = ddl + real_space * " " + "NUMBER(" + line[2] + ")"
            elif table_column_1 == "TIME":
                ddl = ddl + real_space * " " + "TIMESTAMP(" + line[2] + ") WITH LOCAL TIME ZONE"
            else:
                if table_column_1.index(".") > -1:
                    table_det = table_column_1.split(".")
                    cur = con.cursor()
                    sql = "SELECT atc.data_type, atc.data_precision\
                                      FROM all_tab_columns atc\
                                          WHERE atc.table_name = '" + table_det[0].upper() + "'\
                                             AND atc.column_name = '" + table_det[1].upper().strip("\n") + "'"
                    # print(sql)
                    cur.execute(sql)
                    cond = cur.fetchall()
                    cur.close()
                    if len(cond) > 0:
                        for condd in cond:
                            print(condd[0] + str(condd[1]))
                            ddl = ddl + real_space * " " + condd[0] + "(" + str(condd[1]) + ")"
                        if len(line) > 2:
                            if line[2].strip() == "N":
                                if line[2].strip() == "N":
                                    ddl = ddl + " NOT NULL"
                        forign_key.append(table_det)

                        if len(line) > 3:
                            if line[3].strip().upper() == "P":
                                p_key_list.append(line[0].strip().upper())
            # cnt = cnt + 1

            if len(line) > 3:
                if line[3].strip() == "N":
                    ddl = ddl + " NOT NULL"
            ddl = ddl + ","

        ddl = ddl[:-1] + enter_str + ");" + enter_str

        cnt = 1
        for line in all_table:
            if cnt == 1:
                ddl_comment = ddl_comment + "'" + str(line[0]).strip() + "';" + enter_str
                ddl_comment = ddl_comment + "-- Add comments to the columns" + enter_str
            else:
                print(line[0].strip().upper())
                column_name = line[0].strip().upper()
                if column_name == "CREATE_USER":
                    column_comment = "Creation User"
                elif column_name == "CREATE_TIME":
                    column_comment = "Creation Time"
                elif column_name == "CREATE_INSTITUTION":
                    column_comment = "Creation Institution"
                elif column_name == "UPDATE_USER":
                    column_comment = "Update User"
                elif column_name == "UPDATE_TIME":
                    column_comment = "Update Time"
                elif column_name == "UPDATE_INSTITUTION":
                    column_comment = "Update Institution"
                else:
                    column_comment = line[0].strip().upper()

                ddl_comment = ddl_comment + "COMMENT ON column " + file_name + "." + \
                              line[0].strip().upper() + " IS '" + column_comment + "'; " + enter_str
            cnt = cnt + 1

        ddl_p_key = enter_str + "-- Create/Recreate primary, unique and foreign key constraints" + enter_str

        cnt = 1
        for line in all_table:
            if len(line) > 4:
                if line[4].strip().upper() == "P":
                    p_key_list.append(line[0].strip().upper())

    pkey = ""
    for p_key_line in p_key_list:
        if len(pkey) > 0:
            pkey = pkey + ","

        pkey = pkey + p_key_line

    ddl_p_key = ddl_p_key + "ALTER TABLE " + file_name + " add CONSTRAINT " + file_name + "_PK  primary key(" + pkey + "); " + enter_str
    ddl_f_key = ""
    ddl_index = ""

    for id_key in forign_key:
        key_name = id_key[1].strip().upper()
        table_name = id_key[0].strip().upper()
        key_every_line = key_name.split("_")
        key_alias_name = ""

        if len(key_every_line) < 2:
            key_alias_name = key_every_line[1][0:3]

        for e_line in key_every_line:
            key_alias_name = key_alias_name + e_line[0]

        ddl_f_key = ddl_f_key + "ALTER TABLE " + file_name + " add CONSTRAINT " + TABLE_NAME_ABB + "_" + key_alias_name + "_FK foreign key(" + key_name + ") references " + table_name + " (" + key_name + "); " + enter_str

        index_fk_name = TABLE_NAME_ABB + "_" + key_alias_name + "_FK_IDX"
        ddl_index = "CREATE INDEX " + index_fk_name + " on " + file_name + " (" + key_name + ") tablespace ALERT_PHR_IDX;" + enter_str
        # Generate index ddl
        ddl_index_name = index_fk_name
        fo_index = open(gen_table_target_folder + ddl_index_name.upper() + ".idx", "w")
        print("文件名为: ", fo_index.name)
        str_ddl = g_svn_file_header + ddl_index + g_svn_file_footer
        fo_index.write(str_ddl)
        fo_index.close()
        idx_key.append(ddl_index_name.upper() + ".idx")

    # print(ddl + ddl_comment + ddl_p_key + g_svn_file_footer)

    fo = open(gen_table_target_folder + file_name + ".tab", "w")
    # print("文件名为: ", fo.name)
    str_ddl = ddl + ddl_comment + ddl_p_key + g_svn_file_footer
    fo.write(str_ddl)

    fo.close()

    # Generate fk ddl
    if ddl_f_key != "":
        fo = open(gen_table_target_folder + file_name + ".fk", "w")
        print("文件名为: ", fo.name)
        str_ddl = g_svn_file_header + ddl_f_key + g_svn_file_footer
        fo.write(str_ddl)
        fo.close()
        all_ddl_file.fk_name = file_name + ".fk"

    all_ddl_file.cns_name = check_key
    all_ddl_file.idx_name = idx_key
    g_list_ddl_files.append(all_ddl_file)

print(len(g_list_ddl_files))
# Run dml
# ddl_index = 0
for fl in g_list_ddl_files:
    # print(fl.tab_name)
    session = Popen(['SQLPLUS', '-S', 'alertphr/alert@COMPAL_DEV2_CITIZEN'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    session.stdin.write(bytes("@" + gen_table_target_folder + fl.tab_name, 'utf-8'))
    stdout, stderr = session.communicate()
    print(stdout)
    print(stderr)

    # print(fl.fk_name)
    if len(fl.fk_name) > 0:
        session = Popen(['SQLPLUS', '-S', 'alertphr/alert@COMPAL_DEV2_CITIZEN'], stdin=PIPE, stdout=PIPE,
                        stderr=PIPE)
        session.stdin.write(bytes("@" + gen_table_target_folder + fl.fk_name, 'utf-8'))
        stdout, stderr = session.communicate()
        print(stdout)
        print(stderr)

    # print(fl.idx_name)
    if len(fl.idx_name) > 0:
        for idx in fl.idx_name:
            print(idx)
            session = Popen(['SQLPLUS', '-S', 'alertphr/alert@COMPAL_DEV2_CITIZEN'], stdin=PIPE, stdout=PIPE,
                            stderr=PIPE)
            session.stdin.write(bytes("@" + gen_table_target_folder + idx, 'utf-8'))
            stdout, stderr = session.communicate()
            print(stdout)
            print(stderr)

    # print(fl.cns_name)
    if len(fl.cns_name) > 0:
        for cns in fl.cns_name:
            print(cns)
            session = Popen(['SQLPLUS', '-S', 'alertphr/alert@COMPAL_DEV2_CITIZEN'], stdin=PIPE, stdout=PIPE,
                            stderr=PIPE)
            session.stdin.write(bytes("@" + gen_table_target_folder + cns, 'utf-8'))
            stdout, stderr = session.communicate()
            print(stdout)
            print(stderr)
