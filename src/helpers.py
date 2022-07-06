### Module Containing Helper Functions ###
def month_abrv_lkp(abbreviation):
    lkp = {
        'Jan': 'January',
        'Feb': 'February',
        'Mar': 'March',
        'Apr': 'April',
        'May': 'May',
        'June': 'Jun',
        'July': 'Jul',
        'Aug': 'August',
        'Sep': 'September',
        'Oct': 'October',
        'Nov': 'November',
        'Dec': 'December'
    }
    try:
        full_month = lkp[abbreviation]
        return full_month
    except:
        raise ValueError(
            f'Month abbreviation "{abbreviation}" does not match a full month name. Need to update lookup table.')


def check_if_startswith(sub_str, text_list):
    for x in text_list:
        if x.startswith(sub_str):
            tf = True
            value = x[len(sub_str):].strip()
            return tf, value
    return False, None


def game_info_check(header, tbl):
    if header in tbl['Game Info'].to_list():
        value = tbl.loc[tbl['Game Info'] == header, 'Game Info.1'].values[0]
        return True, value
    else:
        return False, None
