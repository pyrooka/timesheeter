#!/usr/bin/env python3

import re
import os
import sys
import signal
import configparser
from datetime import date

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Some global variable
CONFIG_FILE_NAME = '.tsconf'

# Store the actual config.
config = None
# Hold reference to the actual worksheet object.
worksheet = None
# Store the index of the last row on the actual worksheet.
last_row_index = 0


def sigint_handler(signum, frame):
    """
    Handle the SIGINT signal.
    """

    # If we get SIGINT (mostly from CTRL+C) exit from the script.
    if signum == signal.SIGINT:
        sys.exit(1)


def load_config():
    """
    Load the config.
    return:
        False if not found or invalid
        True if valid config is exits and loaded.
    """

    global config

    # Init the config object.
    config = configparser.ConfigParser()

    # Check the config file is exists.
    if not os.path.isfile(CONFIG_FILE_NAME):
        return False

    # So the config is exists, let's read it.
    config.read(CONFIG_FILE_NAME)

    # Now validate.
    validation = validate_config()

    # Return the validation. It contains the result.
    return validation



def validate_config():
    """
    Validate the config file.
    Return a tuple. (True|False, None|'Error message string')
    """

    # Check the secitons.
    if not config.has_section('AUTH'):
        return (False, 'AUTH section is invalid.')

    if not config.has_section('SHEET'):
        return (False, 'SHEET section is invalid.')

    if not config.has_section('INTERFACE'):
        return (False, 'INTERFACE section is invalid.')

    # Check the keys in the sections.
    if not config.has_option('AUTH', 'CredentialPath'):
        return (False, 'CredentialPath option is invalid in the AUTH section.')

    if not config.has_option('SHEET', 'Name'):
        return (False, 'Name option is invalid in the SHEET section.')

    if not config.has_option('SHEET', 'TabTitle'):
        return (False, 'TabTitle option is invalid in the SHEET section.')

    if not config.has_option('INTERFACE', 'DisplayRows'):
        return (False, 'DisplayRows option is invalid in the INTERFACE section.')

    # Check if the credential file exits.
    if not os.path.isfile(config['AUTH']['CredentialPath']):
        return (False, 'Credential\'s path is invalid.')

    # Check if the other options non empty.
    if not config['SHEET']['Name']:
        return (False, 'Spreadsheet name is invalid.')

    if not config['SHEET']['TabTitle']:
        return (False, 'Spreadsheet tab title is invalid.')

    if not config['INTERFACE']['DisplayRows'] or not is_int(config['INTERFACE']['DisplayRows']):
        return (False, 'Interface DisplayRows is invalid.')

    # Everything seems okay.
    return (True, None)


def init():
    """
    Initialize the application and set the worksheet object.
    """

    global worksheet

    # Result of the config load.
    is_loaded, error_message = load_config()

    # If not found print the error message then exit.
    # TODO: Implement edit config in the script.
    if not is_loaded:
        print('ERROR:', error_message)
        sys.exit(1)

    # Get the options.
    cred_path = config['AUTH']['CredentialPath']
    spreadsheet_name = config['SHEET']['Name']
    worksheet_name = config['SHEET']['TabTitle']

    # Authorization.
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name(cred_path, scope)

    try:
        client = gspread.authorize(creds)
    except Exception as e:
        print('Error during the authorization:', e)

    # Get the spreadsheet first.
    try:
        spreadsheet = client.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        print('Error! The spreadsheet is not found:', spreadsheet_name)
        sys.exit(1)

    # Now get the sheet only.
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        print('Error! The worksheet is not found:', worksheet_name)
        sys.exit(1)


def get_last_row_index():
    """
    Set the number of the last row's index, which contains anything.
    """

    global last_row_index
    global worksheet

    # get_all_values() returns a list which length give the number of the rows.
    last_row_index = len(worksheet.get_all_values())


def write_row(row_number, row_data):
    """
    Write the row into the given postion.
    row_number: number of the row to write. (int)
    row_data: tuple with the datas write to cells.
    """

    global worksheet

    for column in range(0, len(row_data)):
        worksheet.update_cell(row_number, column + 1, row_data[column])


def get_rows_from_user(last_row):
    """
    Start a loop and ask the user for inputs.
    last_row: last row in the sheet (list or None).
    """

    global last_row_index
    global worksheet

    last_row = last_row

    # Store previous values.
    entry_date = ''
    project_name = last_row[2] if last_row[2] is not None else ''
    work_hour = last_row[1] if last_row[1] is not None else ''

    # Start an infinity loop.
    while True:
        # New line.
        print('')

        # Get the current date. We get it here, so it will be alway fresh wohoo.
        entry_date = date.today().isoformat()
        # Format the string from 2012-07-27 to 2012.07.27.
        entry_date = entry_date.replace('-', '.') + '.'
        entry_date_raw = input('Date [{0}]: '.format(entry_date))
        entry_date = entry_date_raw if validate_date(entry_date_raw) else entry_date

        project_name_raw = input('Project name [{0}]: '.format(project_name))
        project_name = project_name_raw if project_name_raw is not '' else project_name

        work_hour_raw = input('Work hours [{0}]: '.format(work_hour))
        work_hour = work_hour_raw if work_hour_raw is not '' else work_hour

        description = input('Description: ')

        row = (entry_date, work_hour, project_name, description)

        # If our new row is invalid, start again.
        if not validate_row(row):
            print('\r\nERROR: The given row is invalid. Pleasy try again!')
            continue

        if entry_date == last_row[0]:
            write_row(last_row_index + 1, row)
        else:
            last_row_index += 1
            write_row(last_row_index + 1, row)

        last_row_index += 1
        last_row = row
        print('\r\nEntry saved!\r\n')

        if not show_options(last_row):
            break


def show_options(last_row):
    """
    Show the options. The user can choose what to do.
    last_row: the last row in the worksheet (list).
    """

    while True:
        choose = input('What to do? (Q)uit/(L)ist/(N)ew [N]: ')

        if choose is '' or choose.lower()[0] is 'n':
            return True
        elif choose.lower()[0] is 'q':
            return False
        elif choose.lower()[0] is 'l':
            last_row = print_last_rows()



def validate_row(row):
    """
    Validate the row what a user typed.
    row: tuple
    Return True if valide, otherwise False.
    """

    if not validate_date(row[0]):
        return False

    if not row[1] or not row[2] or not row[3]:
        return False

    return True


def validate_date(date_string):
    """
    Validate the given date string.
    Return True if valid, otherwise return False.
    """

    # Simple regex matching. Only validate on the form not on the values.
    return True if re.match(r'^\d{4}.\d{2}.\d{2}.$', date_string) else False


def is_int(value):
    """
    Try to parse the value to int.
    Return True if can and False if cannot.
    """

    try:
        num = int(value)
    except ValueError:
        return False

    return True


def print_last_rows():
    """
    Get the last rows from the sheet.
    Return the last row in the worksheet which contains data.
    """

    global last_row_index
    global worksheet

    last_row = None
    count=int(config['INTERFACE']['DisplayRows'])

    row_index_from = last_row_index - count if (last_row_index - count) > 0 else 0

    row_index_to = last_row_index if last_row_index > row_index_from else row_index_from + 1

    for row_index in range(row_index_from + 1, row_index_to + 1):
        row = worksheet.row_values(row_index)

        if row[0] is '':
            print('-')
        else:
            print('{0}\t{1}\t{2}\t{3}'.format(row[0], row[1], row[2], row[3]))
            last_row = row

    return last_row


def main():
    """
    The main function.
    """

    # Bind a signal callback.
    signal.signal(signal.SIGINT, sigint_handler)

    # Initialize the whole thing.
    print('Starting initialization...', end='')
    init()
    print('[DONE]')

    # Get the number of the last row.
    print('Fetching last row...', end='')
    get_last_row_index()
    print('[DONE]')

    # Fetch the last rows and write 'em to the output. And get some information 'bout the last row.
    print('Fetching the content of the last rows...\r\n')
    last_row = print_last_rows()

    # Now we can ask the user for the input.
    print('\r\nNow you can enter your data!')
    get_rows_from_user(last_row)


if __name__ == '__main__':
    main()
