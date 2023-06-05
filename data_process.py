import pandas as pd
import json

df_all = pd.read_excel("origin_data/db_out_guc_conf_without_internal.xlsx")

df_type_green = pd.read_excel("origin_data/绿组配置汇总.xlsx", sheet_name="类型分析")
df_type_red = pd.read_excel("origin_data/红组配置汇总.xlsx", sheet_name="类型分析")
df_type = pd.concat([df_type_green, df_type_red])

df_intention_green = pd.read_excel("origin_data/绿组配置汇总.xlsx", sheet_name="意图分析")
df_intention_red = pd.read_excel("origin_data/红组配置汇总.xlsx", sheet_name="意图分析")
df_intention = pd.concat([df_intention_green, df_intention_red])

df_dc_green = pd.read_excel("origin_data/绿组配置汇总.xlsx", sheet_name="约束分析")
df_dc_red = pd.read_excel("origin_data/红组配置汇总.xlsx", sheet_name="约束分析")
df_dc = pd.concat([df_dc_green, df_dc_red])

df_path = pd.read_excel("origin_data/复杂结构信息汇总.xlsx", sheet_name="Path信息统计")
df_dict_list = pd.read_excel("origin_data/复杂结构信息汇总.xlsx", sheet_name="Dict和List信息统计")

with open("origin_data/util_param.json", 'r') as load_f:
    util_param = json.load(load_f)


def get_dependency_constraint():
    return ""


if __name__ == '__main__':
    result = {}

    option_list = {}

    count = 0
    for setting_index, setting_row in df_all.iterrows():
        setting_body = {}

        # 基础配置
        key = setting_row["name"]
        value = str(setting_row["setting"])
        if value == "nan":
            value = ""
        context = setting_row["context"]
        intention = df_intention[df_intention["配置项名称"] == key].iloc[0].at["配置项意图"].split(",")
        category = df_type[df_type["配置项名称"] == key].iloc[0].at["配置项类别"]
        vartype = setting_row["vartype"]
        # if vartype == "string":  # string 类型默认值外加一层单引号
        if category.find("/String") != -1:  # string 类型默认值外加一层单引号
            value = f"'{value}'"
        else:
            value = str(value)

        # constraint 单配置约束
        configuration_type = util_param["configuration_type"][category]

        if configuration_type in ["STR_OTHERS", "STR_BOOL", "NUM_BOOL", "IP", "EMAIL", "DOMAIN_NAME", "UUID"]:
            constraint = configuration_type

        elif configuration_type in ["NUM_ENUM", "STR_ENUM"]:
            enumvals = str(setting_row["enumvals"])
            if enumvals == "nan":  # 部分枚举值不存在，去单配置约束找
                enumvals = df_dc[df_dc["配置项名称"] == key].iloc[0].at["语法约束"]
            constraint = enumvals.replace("{", "[").replace("}", "]").replace("\"", "")
            if configuration_type == "STR_ENUM":  # STR_ENUM 值加上双引号
                constraint = constraint.replace("[", "['").replace("]", "']").replace(",", "','")
            constraint = f"{configuration_type}{constraint}"

        # 无 "SPEED" 类型，无单位：["NUM_OTHERS","PERMISSION"]
        elif configuration_type in ["MEMORY", "TIME", "SPEED", "NUM_OTHERS", "PERMISSION"]:
            number_type = util_param["number_type"][vartype]
            unit = str(setting_row["unit"])
            min_val = str(setting_row["min_val"])
            max_val = str(setting_row["max_val"])

            if unit == "nan":
                unit = ""

            if number_type == "INT":
                min_val = str(int(float(min_val)))
                max_val = str(int(float(max_val)))

            if unit == "8kB":
                unit = ""
                number_type = util_param["number_type"]["8kB"]

            # # 给Time,Memory加默认单位，默认单位去类型约束的备注中找，新单位：byte,us
            # if category.find("default units") != -1:
            #     unit = df_type[df_type["配置项名称"] == key].iloc[0].at["备注"]

            if unit != "":  # 如果存在单位，前面加U
                number_type = f"U{number_type}"

            constraint = f"{configuration_type}[{number_type},{min_val},{max_val},{unit}]"

        elif configuration_type == "PATH":
            path_row = df_path[df_path["配置项名称"] == key].iloc[0]

            absolute_or_relative = path_row.at["absolute_or_relative"]
            create_or_not = path_row.at["create_or_not"]
            file_or_dir = path_row.at["file_or_dir"]

            constraint = f"{configuration_type}[{absolute_or_relative},{create_or_not},{file_or_dir}]"

        elif configuration_type in ["LIST", "DICT"]:
            value_row = df_dict_list[df_dict_list["配置项名称"] == key].iloc[0]

            demo = str(value_row.at["demo"])
            if demo == "nan":
                constraint = "error"
                print(f"{key} {configuration_type}")
                continue

            # TODO: list和dict的value是什么？这里的value不是原始大表中的，而是找出来的
            value = f"'{demo}'"

            value0 = str(value_row.at["value0"])
            value00 = str(value_row.at["value00"]).replace("\"", "")
            value_list = demo.split(value00)

            value_dict = {
                "value0": "''",
                "value00": f"'{value00}'",
            }
            if configuration_type == "DICT":
                value_dict["value000"] = str(value_row.at["value000"]).replace(
                    "\"", "")

            constraint = ""
            for i, val in enumerate(value_list):
                value_index = f"value{i + 1}"
                value_category = value_row.at[value_index]
                value_type = util_param["configuration_type"][value_category]

                if val.find("/String") != -1:  # string 类型默认值外加一层单引号
                    value_dict[value_index] = f"'{val}'"
                    # value = f"{value}|'{val}'"
                else:
                    value_dict[value_index] = val
                    # value = f"{value}|{val}"

                if value_type in ["STR_OTHERS", "STR_BOOL", "NUM_BOOL", "IP", "EMAIL", "DOMAIN_NAME",
                                  "UUID"]:
                    constraint = f"{constraint}|{value_type}"
                elif value_type in ["PATH"]:
                    value_enumvals = str(value_row.at[f"{value_index} enumvals"])
                    constraint = f"{constraint}|{value_type}{value_enumvals}"

                elif value_type in ["NUM_ENUM", "STR_ENUM"]:
                    value_enumvals = str(value_row.at[f"{value_index} enumvals"])

                    value_constraint = value_enumvals.replace("{", "[").replace("}", "]").replace("\"", "'").replace(
                        ", ",
                        ",")  # "$user"
                    if value_type == "STR_ENUM":  # STR_ENUM 值加上双引号
                        if value_constraint.find(")") != -1:  # 带括号，括号里面有,
                            value_constraint = value_constraint.replace("[", "['").replace("]", "']").replace("),",
                                                                                                              ")','")
                        else:
                            value_constraint = value_constraint.replace("[", "['").replace("]", "']").replace(",",
                                                                                                              "','")

                    constraint = f"{constraint}|{value_type}{value_constraint}"
                # 无 "SPEED" 类型，无单位：["NUM_OTHERS","PERMISSION"]
                elif value_type in ["MEMORY", "TIME", "SPEED", "NUM_OTHERS", "PERMISSION", "PORT"]:
                    if value_type == "NUM_OTHERS":
                        number_type = util_param["number_type"][value_category]
                    else:
                        number_type = "INT"

                    unit = str(value_row[f"{value_index} unit"])
                    min_val = str(value_row[f"{value_index} min_val"])
                    max_val = str(value_row[f"{value_index} max_val"])

                    if unit == "nan":
                        unit = ""

                    if number_type == "INT":
                        min_val = str(int(float(min_val)))
                        max_val = str(int(float(max_val)))

                    if unit == "8kB":
                        unit = ""
                        number_type = util_param["number_type"]["8kB"]

                    # # 给Time,Memory加默认单位，默认单位去类型约束的备注中找，新单位：byte,us
                    # if category.find("default units") != -1:
                    #     unit = df_type[df_type["配置项名称"] == key].iloc[0].at["备注"]

                    if unit != "":  # 如果存在单位，前面加U
                        number_type = f"U{number_type}"

                    constraint = f"{constraint}|{value_type}[{number_type},{min_val},{max_val},{unit}]"

            remove_index = constraint.find("|")
            if remove_index == 0:
                # value = value[1:]
                constraint = constraint[1:]

            setting_body.update(value_dict)

        # TODO：dependency_constraint 多配置约束
        dependency_constraint = get_dependency_constraint()

        setting_body.update({
            "key": key,
            "value": value,
            "context": context,
            "category": category,
            "intention": intention,
            "constraint": constraint,
            "dependency_constraint": dependency_constraint
        })

        count += 1
        option_list[str(count)] = setting_body
        result = {
            "option_list": option_list,
            "format": "$key = $value"
        }

    with open("output/option_list.json", "w") as f:
        json.dump(result, f)
