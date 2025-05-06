#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import undetected_chromedriver as uc
from datetime import datetime
import csv

# Variables globales
availableDoctors = []
validSectors = [
    "Établissement conventionné",
    "Conventionné secteur 1", 
    "Conventionné secteur 2",
    "Conventionné secteur 1 avec OPTAM",
    "Conventionné secteur 2 avec OPTAM",
    "Secteur 3 (non-conventionné)"
]
lastDoctorIndex = 0

# Configuration de la recherche
print("\nConfiguration de la recherche Doctolib (appuyez sur Entrée pour les valeurs par défaut)")

SEARCH_STRING = input(f"Spécialité médicale recherchée [Cardiologue]: ") or "Cardiologue"
GEOGRAPHICAL = input(f"Localisation géographique [Paris]: ") or "Paris"

NB_DOCTEURS = int(input(f"Nombre de médecins à récupérer [2]: ") or 2)
START_DATE = input(f"Date de début de recherche (JJ/MM/AAAA) [15/01/2025]: ") or "15/01/2025"
END_DATE = input(f"Date de fin de recherche (JJ/MM/AAAA) [23/12/2025]: ") or "23/12/2025"

print("\nOptions de conventionnement disponibles:")
for i, sector in enumerate(validSectors, 1):
    print(f"{i}. {sector}")
sector_choice = int(input(f"Type de convention (1-6) [5]: ") or 5)
ASSURANCE_TYPE = validSectors[sector_choice-1]

CONSULTATION_TYPE = input(f"Type de consultation (Présentiel/Visio) [Présentiel]: ") or "Présentiel"
MAX_PRICE = int(input(f"Prix maximum de consultation [100]: ") or 100)
MIN_PRICE = int(input(f"Prix minimum de consultation [0]: ") or 0)

print("\nParamètres configurés avec succès!")

# Initialisation du navigateur
driver = uc.Chrome()
driver.get("https://www.doctolib.fr/")

# Fonction pour convertir le mois en format numérique
def convert_month(month):
    if month == "janvier":
        return "01"
    elif month == "février":
        return "02"
    elif month == "mars":
        return "03"
    elif month == "avril":
        return "04"
    elif month == "mai":
        return "05"
    elif month == "juin":
        return "06"
    elif month == "juillet":
        return "07"
    elif month == "août":
        return "08"
    elif month == "septembre":
        return "09" 
    elif month == "octobre":
        return "10"
    elif month == "novembre":
        return "11"
    elif month == "décembre":
        return "12" 

# Fonction pour récupérer les médecins
def fetch_doctors(availableDoctors):
    global lastDoctorIndex
    
    # Défilement de la page pour mettre à jour le DOM (Afficher les calendriers)
    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    
    # Récupération des éléments des médecins
    results = driver.find_elements(By.XPATH, "//div[contains(@class, 'dl-card dl-card-bg-white dl-card-variant-default dl-card-border')]")
    
    print(f"DEBUG: Nombre total de médecins sur cette page: {len(results)}")
    print(f"DEBUG: Index du dernier médecin traité: {lastDoctorIndex}")
    
    start_index = lastDoctorIndex
    print(f"DEBUG: Démarrage du traitement à l'index: {start_index}")
    
    if start_index >= len(results):
        print(f"DEBUG: L'index de départ ({start_index}) est supérieur au nombre de résultats ({len(results)}), réinitialisation à 0")
        lastDoctorIndex = 0
        start_index = 0
    
    end_index = min(start_index + 1, len(results))
    
    for i in range(start_index, end_index):
        if i > start_index:
            driver.refresh()
            time.sleep(2)
            results = driver.find_elements(By.XPATH, "//div[contains(@class, 'dl-card dl-card-bg-white dl-card-variant-default dl-card-border')]")
            if i >= len(results):
                print(f"DEBUG: Index {i} hors limites après rafraîchissement (total: {len(results)})")
                break
        
        try:
            result = results[i]
            doctor_info = {}
            lastDoctorIndex = i + 1
            print(f"DEBUG: Traitement du médecin à l'index {i}, prochain index sera {lastDoctorIndex}")
    
            # Vérification si le médecin est disponible en visio si la recherche est en visio
            if CONSULTATION_TYPE == "Visio":
                try: 
                    visio_icon = result.find_element(By.XPATH, ".//div[contains(@class, 'absolute -right-8 -bottom-8 bg-white rounded-full w-24 h-24 flex items-center justify-center shadow-md')]")
                    doctor_info['consultation_type'] = "Visio"
                except Exception as e:
                    print(f"DEBUG: Médecin non disponible en visio, passage au suivant")
                    continue
            
            # Recherche du secteur du médecin
            try:
                sector_found = False
                all_paragraphs = result.find_elements(By.XPATH, ".//p")
                for paragraph in all_paragraphs:
                    try:
                        # Récupération du texte du paragraphe
                        text = paragraph.text.strip()
                        if "Conventionné" in text:
                            print(f"DEBUG: Texte conventionné trouvé: '{text}'")
                            if text == ASSURANCE_TYPE:
                                doctor_info['sector'] = text
                                print(f"DEBUG: Secteur compatible: {text}")
                                sector_found = True
                                break
                            else:
                                print(f"DEBUG: Secteur incompatible: {text} != {ASSURANCE_TYPE}")
                    except Exception as e:
                        continue
                
                if not sector_found:
                    print(f"DEBUG: Aucun secteur compatible trouvé, passage au médecin suivant")
                    continue
                    
            except Exception as e:
                print(f"DEBUG: Erreur lors de la recherche du secteur: {e}")
                continue
                
            # Récupération du nom et du lien du médecin
            try:
                name = result.find_element(By.XPATH, ".//h2[contains(@class, 'dl-text-body') and contains(@class, 'dl-text-bold')]")
                doctor_info['name'] = name.text
                doctorHref = result.find_element(By.XPATH, ".//a[contains(@class, 'dl-text-decoration-none')]")
                doctor_info['href'] = doctorHref.get_attribute('href')
                print(f"DEBUG: Médecin trouvé: {name.text}")
            except Exception as e:
                print(f"DEBUG: Erreur lors de la récupération du nom/lien: {e}")
                continue
                
            # Récupération de l'adresse du médecin
            try:
                address_elements = result.find_elements(By.XPATH, ".//div[contains(@class, 'flex-wrap gap-x-4')]//p")
                address = " ".join([elem.text for elem in address_elements if elem.text])
                doctor_info['address'] = address
            except Exception as e:
                doctor_info['address'] = "Non disponible"
                print(f"DEBUG: Adresse non disponible: {e}")

            # Récupération de la date du prochain rendez-vous
            try:
                availableDate = result.find_element(By.XPATH, ".//button[contains(@class, 'dl-button')]//span[contains(text(), 'Prochain RDV')]/..")
                date = availableDate.text.split('Prochain RDV le')[1].strip()
                date = date.split(' ')[0] + "/" + convert_month(date.split(' ')[1]) + "/" + date.split(' ')[2]
               
                # Vérification si la date est dans la plage de dates
                if datetime.strptime(date, "%d/%m/%Y").timestamp() >= datetime.strptime(START_DATE, "%d/%m/%Y").timestamp() and datetime.strptime(date, "%d/%m/%Y").timestamp() <= datetime.strptime(END_DATE, "%d/%m/%Y").timestamp():
                   try:
                        doctor_info['next_appointment'] = None 

                        # Défilement de la page pour mettre à jour le DOM (Afficher les calendriers)
                        time.sleep(1)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", availableDate)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", availableDate)
                        time.sleep(1)
                        
                        # Attente que les calendriers soient chargés
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, ".//div[contains(@class, 'flex flex-1 flex-col gap-8 min-w-0')]"))
                        )

                            # Récupération des tables des horaires
                        tables = result.find_elements(By.XPATH, ".//div[contains(@class, 'flex flex-1 flex-col gap-8 min-w-0')]")
                        for table in tables:
                            try:
                                # Récupération de la première date disponible
                                first_slot = table.find_element(By.TAG_NAME, "button")
                                time_text = first_slot.find_element(By.TAG_NAME, "span").text
                                doctor_info['next_appointment'] = f"{date} {time_text}"
                                break 
                            except Exception as e:
                                print(f"DEBUG: Erreur lors de la lecture des horaires : {e}")
                                continue
                   except Exception as e:
                        print(f"DEBUG: Erreur lors du traitement du docteur : {e}")
                else:
                    # Si aucun rendez-vous disponible, on passe au médecin suivant
                    doctor_info['next_appointment'] = None
                        
                    # Défilement de la page pour mettre à jour le DOM (Afficher les calendriers)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", availableDate)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", availableDate)
                    time.sleep(1)
                    
                    # Attente que les calendriers soient chargés
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, ".//div[contains(@class, 'flex flex-1 flex-col gap-8 min-w-0')]"))
                    )
                    
                    # Récupération des tables des horaires
                    tables = result.find_elements(By.XPATH, ".//div[contains(@class, 'flex flex-1 flex-col gap-8 min-w-0')]")
                    for table in tables:
                        try:
                            # Récupération de la première date disponible
                            first_slot = table.find_element(By.TAG_NAME, "button")
                            time_text = first_slot.find_element(By.TAG_NAME, "span").text
                            doctor_info['next_appointment'] = f"{date} {time_text}"
                            break 
                        except Exception as e:
                            print(f"DEBUG: Erreur lors de la lecture des horaires : {e}")
                            continue
        
            except Exception as e:
                print(f"DEBUG: Erreur lors de la récupération de la date: {e}")
            
            print(f"DEBUG: Préparation à récupérer les tarifs pour {doctor_info['name']}")

            # Récupération des tarifs
            alt_fetch_doctor_prices(doctor_info)
            print(f"DEBUG: Après récupération des tarifs, nombre total de médecins: {len(availableDoctors)}")
            if(len(availableDoctors) >= NB_DOCTEURS):
                print(f"DEBUG: Nombre cible de médecins atteint ({NB_DOCTEURS}), arrêt de la recherche")
                break
        except Exception as e:
            print(f"DEBUG: Erreur générale lors du traitement du médecin {i}: {e}")
            lastDoctorIndex = i + 1
    
    print(f"DEBUG: Fin de boucle - Index actuel: {lastDoctorIndex}, Nombre total médecins: {len(results)}")
    if lastDoctorIndex >= len(results):
        print(f"DEBUG: Tous les médecins de cette page ont été traités, passage à la page suivante")
        lastDoctorIndex = 0
        return True 
    print(f"DEBUG: Il reste des médecins à traiter sur cette page")
    return False

# Fonction pour récupérer les tarifs
def alt_fetch_doctor_prices(doctor):

    # Récupération de l'URL actuelle
    current_url = driver.current_url
    print(f"DEBUG: URL actuelle avant visite du profil médecin: {current_url}")
    result = False
    

    try:
        print(f"DEBUG: Visite de la page du médecin: {doctor['href']}")
        driver.get(doctor['href'])
        time.sleep(3)

        # Attente que la page soit chargée
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dl-profile-card-section"))
        )

        # Récupération des éléments de tarif
        price_elements = driver.find_elements(By.CLASS_NAME, "dl-profile-fee")
        prices = []
        price_values = []
        
        print(f"DEBUG: Nombre d'éléments de tarif trouvés: {len(price_elements)}")

        # Parcours des éléments de tarif
        for element in price_elements:
            try:
                # Récupération du nom du service
                service = element.find_element(By.CLASS_NAME, "dl-profile-fee-name").text.strip()
                price_text = element.find_element(By.CLASS_NAME, "dl-profile-fee-tag").text.strip()
                
                print(f"DEBUG: Tarif trouvé - {service}: {price_text}")

                # Ajout du tarif à la liste
                prices.append(f"{service}: {price_text}")
                
                # Vérification si le tarif est un prix minimum et maximum
                if "€ à " in price_text:
                    parts = price_text.split("€ à ")
                    min_price = float(parts[0].replace(",", ".").strip())
                    max_price = float(parts[1].replace("€", "").replace(",", ".").strip())
                    price_values.append((min_price + max_price) / 2)
                else:
                    clean_price = price_text.replace("€", "").replace(",", ".").strip()
                    if clean_price and clean_price.replace(".", "", 1).isdigit():
                        price_values.append(float(clean_price))
                
            except Exception as e:
                print(f"DEBUG: Erreur lors de la lecture d'un tarif: {e}")
                continue
        
        # Vérification si des tarifs ont été trouvés
        if price_values:
            moyenne = sum(price_values) / len(price_values)
            print(f"DEBUG: Prix extraits: {price_values}, Moyenne: {moyenne:.2f}€")
            if MIN_PRICE <= moyenne <= MAX_PRICE:
                doctor['prices'] = prices
                print(f"DEBUG: Tarifs acceptables (moyenne: {moyenne:.2f}€): {prices}")
                availableDoctors.append(doctor)
                result = True
            else:
                print(f"DEBUG: Moyenne des prix ({moyenne:.2f}€) hors plage autorisée ({MIN_PRICE}-{MAX_PRICE}€)")
                result = False
        else:
            doctor['prices'] = "Non communiqués"
            print("DEBUG: Aucun tarif trouvé - Ajout du médecin quand même")
            availableDoctors.append(doctor)
            result = True
            
    except Exception as e:
        # Erreur lors de la récupération des tarifs
        print(f"DEBUG: Erreur lors de la récupération des tarifs: {e}")
        doctor['prices'] = "Erreur de récupération"
        availableDoctors.append(doctor)
        result = True
    
    finally:
        try:
            # Retour à la page de recherche
            print(f"DEBUG: Retour à la page de recherche: {current_url}")
            driver.get(current_url)
            time.sleep(3)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'dl-card dl-card-bg-white dl-card-variant-default dl-card-border')]"))
            )
            print("DEBUG: Page de recherche chargée avec succès")
        except Exception as e:
            # Erreur lors du retour à la page de recherche
            print(f"DEBUG: Erreur lors du retour à la page de recherche: {e}")
    
    return result


try:
    # Attente que la page soit chargée
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Attente que le bouton de consentement soit présent
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "didomi-notice-agree-button"))
    )

    # Clic sur le bouton de consentement
    driver.find_element(By.ID, "didomi-notice-agree-button").click()

    # Attente que l'input de recherche soit présent
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "searchbar-query-input"))
    )
    print("Found")

    # Remplissage de l'input de recherche
    name_input = driver.find_element(By.CLASS_NAME, "searchbar-query-input")
    name_input.send_keys(SEARCH_STRING)
    time.sleep(0.5)
    name_input.send_keys(Keys.ENTER)

    # Remplissage de l'input de recherche
    place_input = driver.find_element(By.CLASS_NAME, "searchbar-place-input")
    place_input.send_keys(GEOGRAPHICAL)
    time.sleep(0.5)
    place_input.send_keys(Keys.ENTER)
    
    time.sleep(0.5)
    button_seach = driver.find_element(By.CLASS_NAME, "searchbar-submit-button")
    button_seach.click()

    # Attente que les médecins soient chargés
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'dl-card dl-card-bg-white dl-card-variant-default dl-card-border')]"))
    )

    time.sleep(1)

    # Boucle pour récupérer les médecins
    while(len(availableDoctors) < NB_DOCTEURS):
        print(f"DEBUG: ===== NOUVELLE ITÉRATION =====")
        print(f"DEBUG: Recherche de médecins {len(availableDoctors)}/{NB_DOCTEURS}")
        page_completed = fetch_doctors(availableDoctors)
        
        # Vérification si le nombre de médecins cible est atteint
        if len(availableDoctors) >= NB_DOCTEURS:
            print(f"DEBUG: Nombre de médecins cible atteint: {len(availableDoctors)}/{NB_DOCTEURS}")
            break

        # Vérification si la page est complètement traitée
        if page_completed:
            print(f"DEBUG: Page actuelle complètement traitée, tentative de passage à la page suivante")
            try:
                time.sleep(3)

                # Attente que le bouton de passage à la page suivante soit présent
                next_page = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Page suivante')]"))
                )
                
                # Défilement de la page pour mettre à jour le DOM (Afficher le bouton de passage à la page suivante)
                driver.execute_script("window.scrollTo(0, 0)")
                time.sleep(1)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", next_page)
                time.sleep(2)
                
                try:
                    # Clic sur le bouton 'Page suivante'
                    print("DEBUG: Clic sur le bouton 'Page suivante'")
                    next_page.click()
                except:
                    print("DEBUG: Utilisation de JavaScript pour cliquer sur 'Page suivante'")
                    driver.execute_script("arguments[0].click();", next_page)
                    
                time.sleep(3)
                print("DEBUG: Passage à la page suivante réussi")
                
            except Exception as e:
                print(f"DEBUG: Impossible de trouver le bouton Page Suivant ou de passer à la page suivante : {e}")
                
                try:
                    driver.title
                except:
                    print("DEBUG: La connexion avec le navigateur a été perdue. Arrêt de la recherche.")
                    break
                    
                break
        else:
            print(f"DEBUG: Il reste des médecins à traiter sur la page actuelle, pas de passage à la page suivante")

    # Exportation des résultats dans un fichier CSV
    with open('docteurs.csv', 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['name', 'sector', 'address', 'next_appointment', 'prices', 'href', 'consultation_type']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for doctor in availableDoctors:
            doctor_data = doctor.copy()
            
            if isinstance(doctor_data.get('prices'), list):
                doctor_data['prices'] = ' | '.join(doctor_data['prices'])
            elif doctor_data.get('prices') is None:
                doctor_data['prices'] = "Non communiqués"
                
            for field in fieldnames:
                if field not in doctor_data:
                    doctor_data[field] = ""
                    
            writer.writerow(doctor_data)
            
    print("Les résultats ont été exportés dans docteurs.csv")
    print(f"Nombre de médecins exportés : {len(availableDoctors)}")
    
except Exception as e:
    print(f"Erreur dans la boucle principale : {e}")
finally:
    driver.quit()
