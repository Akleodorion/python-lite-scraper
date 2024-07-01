import time
import subprocess
from pyvirtualdisplay import Display
import nodriver as uc
from selectolax.parser import HTMLParser
import requests
import json

serverUrl = 'https://hdv-watcher-3be496b8731a.herokuapp.com/scraper/scrap'
localUrl = 'http://localhost:3000/scraper/scrap'

# Fonction qui permet de récupérer les 15 objets d'une page.
def retrieve_page_objects(tree: HTMLParser):
    tr_nodes = tree.css("tbody tr")
    objects = [ get_dictionnary_from_object(tr_node) for tr_node in tr_nodes]
    return objects

# Fonction qui retourne un dictionnaire avec toute les informations de l'objet
def get_dictionnary_from_object(tr_node: HTMLParser):
    object = {
        "img_url": retrieve_object_img_url(tr_node),
        "name": retrieve_object_name(tr_node),
        "unit_price": retrieve_object_price(tr_node,1),
        "ten_price": retrieve_object_price(tr_node,10),
        "hundred_price": retrieve_object_price(tr_node,100),
        "item_type": retrieve_object_type(tr_node)
    }
    return object

# Fonction qui permet de récupérer l'url d'un objet
def retrieve_object_img_url(tree: HTMLParser):
    return tree.css_first("img").attributes["src"]

# Fonction qui permet de récupérer le nom d'un objet
def retrieve_object_name(tree: HTMLParser):
    try:
        name = tree.css_first("p").text()
    except AttributeError as e:
        raise AttributeError from e
    return name

# Fonction qui permet de récupérer le type d'un objet
def retrieve_object_type(tree: HTMLParser):
    try:
        itemType = tree.css("td")[1].css("p")[-1].text()
    except IndexError as e:
        return ""
    return remove_chars_from_string(itemType, "[]")


def remove_chars_from_string(name: str, chr: list):
    for x in range(len(chr)):
            name = name.replace(chr[x],"")
    return name

# Fonction qui permet de récupérer le prix au lot de 1 d'un objet
def retrieve_object_price(tree: HTMLParser, qty: int):
    dic = {1: 5, 10: 6, 100: 7}
    try:
        price = tree.css("td")[dic[qty]].attributes["data-order"]
    except IndexError as e:
        return 0.0
    except AttributeError as e:
        return 0.0
    return price


# Fonction qui permet de changer de page si le bouton n'est pas disabled.
def next_page(tree: HTMLParser):
    tree.css_first("a.paginate_button.next")
    pass

# Fonction qui gère l'attente du chargement de la page.
async def await_site_initial_loading(tab: uc.core.tab.Tab):
    try:
        print("On attends 30 secondes ...")
        time.sleep(30)
        await tab.find("Prix multi-serveur")
    except TimeoutError as e:
        print("Nous n'avons pas passer cloudflare !!!!")
        raise TimeoutError from e

def splitArrayInBatches(batchSize: int, objectArray: list):
    newArray = []
    numberOfBatches = (len(objectArray) / batchSize).__ceil__()
    for i in range(numberOfBatches):
        startIndex = i * batchSize
        endIndex = (i + 1) * batchSize
        newArray.append(objectArray[startIndex:endIndex])
    pass
    return newArray

async def lookForStrOnPage(message: str, tab):
    #! verification de la mise à jour des prix.
    try:
        await tab.find("minutes")
    except TimeoutError as e:
        raise TimeoutError

async def fetchAllData(tab, max_page_number):
    objects = []

    for i in range(max_page_number - 1):
        next_button = await tab.find("a.paginate_button.next")
        str = await tab.evaluate('document.documentElement.outerHTML')
        tree = HTMLParser(str)
        objects.append(retrieve_page_objects(tree))
        await next_button.click()
        time.sleep(0.03)

    return objects

def patchRequest(batch: list, url: str, compteur: int):
    # Convertir les données en JSON
    payload = json.dumps(batch)

    headers = {'Content-Type': 'application/json'}
    response = requests.patch(url, data=payload, headers=headers)

    print(f"Nous faisons la requête n°: {compteur}")
    if response.status_code == 200 or response.status_code == 204:
        print('Requête Patch réussie !')
    else:
        print(f'Erreur lors de la requête PATCH : {response.status_code}, {response.text}')

async def getNumberOfPages(tab):
    list = await tab.select_all("div.dataTables_paginate a")
    return int(list[6].text)

async def getBrowserOrError():
    try:
        print("Ouverture du navigateur")
        browser = await uc.start(no_sandbox=True, headless=False)
        return browser
    except Exception as e:
        killAllChromiumAliveInstances()
        return       

def killAllChromiumAliveInstances():
    subprocess.run(["pkill chromium"], shell=True, capture_output=True, text=True)

async def main():
    display = Display(visible=0, size=(1080,720))
    display.start()
    browser = await getBrowserOrError()

    if not(browser):
        try:
            print("Deuxième ouverture")
            browser = await uc.start(no_sandbox=True, headless=False)
            return browser
        except Exception as e:
            print(f"Nous n'avons pas pu ouvrir le navigateur: {e}")     

    print("Navigation vers Vulbis.com")
    tab = await browser.get("https://vulbis.com")

    print("Nous attendons le chargement du site ...")
    await await_site_initial_loading(tab)

    try:
        await lookForStrOnPage("minutes", tab)
    except TimeoutError as e:
        print("Le site n'a pas encore mis à jour les prix de l'hdv.")

    max_page_number = await getNumberOfPages(tab)
    objects = await fetchAllData(tab, max_page_number)
    objectsBatches = splitArrayInBatches(50,objects)
    print(f'Nous avons récupérer les {len(objectsBatches)} batches.\nNous commençons les requêtes.')
    compteur = 0

    for batch in objectsBatches:
        patchRequest(batch, serverUrl, compteur)
        compteur = compteur + 1
    display.stop()


uc.loop().run_until_complete(main())
