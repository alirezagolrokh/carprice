import requests
import re
import time
from bs4 import BeautifulSoup


# This function is responsible for receiving up to 150 data.
# If there were not 150! Returns Whatever received data.
def _car_info(_brand, _model, _package):
    car_information = []
    page_number = 1

    while len(car_information) < 150:
        if _package:
            _result = requests.get('https://bama.ir/car/'+_brand+'/'+_model+'/'+_package +
                                   '?instalment=0&page=' + str(page_number))
        else:
            _result = requests.get('https://bama.ir/car/'+_brand+'/'+_model +
                                   '/all-trims?instalment=0&page=' + str(page_number))

        _soup = BeautifulSoup(_result.content, 'html.parser')

        page_link = _soup.find('link', attrs={'rel': 'canonical'})

        if page_link.attrs['href'] == 'https://bama.ir/car':
            break

        # Get cars born year of page
        born = _soup.find_all('h2', attrs={'class': 'persianOrder'})
        born = re.findall(r'.*\s+(\d+)،', str(born))

        # Get cars prce of page
        prices = _soup.find_all(attrs={'itemprop': 'price'})
        _regex_pattern = r'<.*?content=\"(.*?)\" itemprop=\"price\">.*?</span>'
        prices = re.findall(_regex_pattern, str(prices))

        # Get cars kilometer of page
        kilometers = _soup.find_all('p', attrs={'class': 'price hidden-xs'})
        _regex_pattern = r'<p class=\"price hidden-xs\">(.*?)</p>'
        kilometers = re.findall(_regex_pattern, str(kilometers))

        _regex_pattern = r' کارکرد (\d+),*(\d+) کیلومتر'
        kilometers = list(map(lambda km: re.sub(_regex_pattern, '\g<1>\g<2>', km), kilometers))

        kilometers = list(map(lambda km: km.replace(' کارکرد صفر کیلومتر', '0'), kilometers))

        for i in range(0, len(kilometers)):
            if int(prices[i]) > 0 and kilometers[i].isdecimal() and born[i].isdecimal():
                car_information.append([int(born[i]), int(kilometers[i]), int(prices[i])])
            if len(car_information) == 150:
                break

        page_number += 1
    return car_information


# save received data to database and delete duplicate records.
# The table name is (brand + model + package)
def save_to_table(_model_detail):
    import mysql.connector

    db_name = input('Enter your database name to connecting:\n')
    password = input('Enter your mysql password to connecting:\n')
    username = input('Enter your mysql user name to connecting:\n')

    db = mysql.connector.connect(user=username, password=password, host='127.0.0.1',
                                 database=db_name)
    cursor = db.cursor()

    table_name = input("Enter table name to create:\n")

    query = 'CREATE TABLE IF NOT EXISTS %s(born INT, kilometer INT, price BIGINT) ' \
            'CHARACTER SET=utf8mb4' % table_name
    cursor.execute(query)

    for born, km, price in _model_detail:
        cursor.execute('INSERT INTO %s VALUES(%d, %d, %d)' % (table_name, born, km, price))
    db.commit()

    # Delete duplicate record
    cursor.execute('CREATE TABLE copy LIKE %s' % table_name)

    cursor.execute('INSERT INTO copy '
                   'SELECT DISTINCT * FROM %s' % table_name)

    cursor.execute('DROP TABLE %s '% table_name)
    cursor.execute('ALTER TABLE copy RENAME TO %s' % table_name)

    # Select data from table
    query = 'SELECT * FROM %s' % table_name
    cursor.execute(query)

    # Get data table and Pour to output field type is list
    output = []
    for born, km, price in cursor:
        output.append([born, km, price])

    cursor.close()
    db.close()
    return output


# main
while True:
    # Get brand from site
    result = requests.get('https://bama.ir/car')
    soup = BeautifulSoup(result.content, 'html.parser')
    result = soup.find('select', attrs={'name': 'selectedTopBrand'})
    brands = re.findall(r'<option value="\d+,(.*)">.*</option>', str(result))

    for car in brands:
        print(car)

    # Get brand from user
    brand = input('Enter one of the above brands:\n')
    while not brands.count(brand):
        del brand
        brand = input('This brand does not exist! re-enter brand:\n')

    # Get model of brand from site
    result = requests.get('https://bama.ir/car/' + brand)
    soup = BeautifulSoup(result.content, 'html.parser')
    result = soup.find('section', attrs={'class': 'search-new-page'})

    models = re.match(r'.*\"TopModelList\":\[(.+)\],\"TopTrimList\".*', str(result))
    regex_pattern = r'{\"Disabled\":false,\"Group\":null,\"Selected\":false,\"Text\":\".+?\",\"Value\":\"\d+,(.+?)\"}'
    models = re.findall(regex_pattern, models.group(1))

    for model in models:
        print(model)

    # Get model of brand from user
    model = input('Enter one of the above models:\n')
    while not models.count(model):
        del model
        model = input('Model not exist! re-enter model:\n')

    # if package of model from site
    result = requests.get('https://bama.ir/car/' + brand + '/' + model)
    soup = BeautifulSoup(result.content, 'html.parser')
    result = soup.find('section', attrs={'class': 'search-new-page'})

    packages = re.search(r'.*\"TopTrimList\":\[(.+)\],\"CarAdResults\".*', str(result))

    if packages:
        regex_pattern = r'{\"Disabled\":false,\"Group\":null,\"Selected\":false,\"Text\":\".+?\",\"Value\":\"\d+,(.+?)\"}'
        packages = re.findall(regex_pattern, packages.group(1))

        for package in packages:
            print(package)

        package = input('Enter one of the above package of '+brand+' '+model+':\n')
        while not packages.count(package):
            del package
            package = input('Package not exist! re-enter package:\n')
    else:
        package = None

    # call function get car info with argument brand , model , package of car
    info = _car_info(brand, model, package)

    while len(info) < 20:
        print('The information obtained from this model or brand is low for prediction.\n'
              'Please select another model or brand...')
        time.sleep(2.5)
        break
    if len(info) >= 20:
        # Get Saved data of car
        info = save_to_table(info)

        # Getting user information right
        km = input('Enter kilometer you want:\n')
        py = input('Enter the production year you want:\n')

        # Separating information for fit
        x = []
        y = []
        for inx in info:
            x.append(inx[0:2])
            y.append(inx[2])

        from sklearn import tree
        clf = tree.DecisionTreeClassifier()

        # Fit separated information
        clf.fit(x, y)
        user_want = [[py, km]]
        user_want = clf.predict(user_want)
        print('Estimated price for {} {} {} , year = {} , kilometer = {} is: {}'
              .format(brand, model, package, py, km, user_want[0]))
        break