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
import re

print("""
 ___              _      
|  _ \  ___   ___| |_ ___  ___  ___ _ __ __ _ _ __  
| | | |/ _ \ / __| __/ _ \/ __|/ __| '__/ _` | '_ \ 
| |_| | (_) | (__| || (_) \__ \ (__| | | (_| | |_) |
|____/ \___/ \___|\__\___/|___/\___|_|  \__,_| .__/ 
                                             |_|    
""")

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

def validate_date(date_str):
    """Valide le format de la date (JJ/MM/AAAA) et s'assure que la date est valide"""
    try:
        # Vérifie le format avec une regex
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
            return False, "Le format de la date doit être JJ/MM/AAAA"
        
        # Convertit en objet datetime pour vérifier la validité
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        
        # Vérifie que la date n'est pas dans le passé
        if date_obj < datetime.now():
            return False, "La date ne peut pas être dans le passé"
            
        return True, date_obj
    except ValueError:
        return False, "La date n'est pas valide"

def validate_number(value, min_val=None, max_val=None):
    """Valide qu'une valeur est un nombre et dans les limites spécifiées"""
    try:
        num = int(value)
        if min_val is not None and num < min_val:
            return False, f"La valeur doit être supérieure ou égale à {min_val}"
        if max_val is not None and num > max_val:
            return False, f"La valeur doit être inférieure ou égale à {max_val}"
        return True, num
    except ValueError:
        return False, "La valeur doit être un nombre entier"

def validate_consultation_type(consultation_type):
    """Valide le type de consultation"""
    valid_types = ["Présentiel", "Visio"]
    if consultation_type not in valid_types:
        return False, f"Le type de consultation doit être l'un des suivants: {', '.join(valid_types)}"
    return True, consultation_type

def get_validated_input(prompt, default_value, validation_func, *args):
    """Demande une entrée à l'utilisateur et la valide"""
    while True:
        value = input(f"{prompt} [{default_value}]: ") or default_value
        is_valid, result = validation_func(value, *args)
        if is_valid:
            return result
        print(f"Erreur: {result}")
        print("Veuillez réessayer.")

# Configuration de la recherche
print("\nConfiguration de la recherche Doctolib (appuyez sur Entrée pour les valeurs par défaut)")

SEARCH_STRING = input(f"Spécialité médicale recherchée [Cardiologue]: ") or "Cardiologue"
GEOGRAPHICAL = input(f"Localisation géographique [Paris]: ") or "Paris"

NB_DOCTEURS = get_validated_input(
    "Nombre de médecins à récupérer",
    "2",
    validate_number,
    1,  # min_val
    100  # max_val
)

START_DATE = get_validated_input(
    "Date de début de recherche (JJ/MM/AAAA)",
    "20/06/2025",
    validate_date
)

END_DATE = get_validated_input(
    "Date de fin de recherche (JJ/MM/AAAA)",
    "23/12/2025",
    validate_date
)

# Vérification que la date de fin est après la date de début
if END_DATE < START_DATE:
    print("Erreur: La date de fin doit être après la date de début")
    END_DATE = get_validated_input(
        "Date de fin de recherche (JJ/MM/AAAA)",
        "23/12/2025",
        validate_date
    )

print("\nOptions de conventionnement disponibles:")
for i, sector in enumerate(validSectors, 1):
    print(f"{i}. {sector}")

sector_choice = get_validated_input(
    "Type de convention",
    "5",
    validate_number,
    1,  # min_val
    len(validSectors)  # max_val
)
ASSURANCE_TYPE = validSectors[sector_choice-1]

CONSULTATION_TYPE = get_validated_input(
    "Type de consultation",
    "Présentiel",
    validate_consultation_type
)

MAX_PRICE = get_validated_input(
    "Prix maximum de consultation",
    "100",
    validate_number,
    0  # min_val
)

MIN_PRICE = get_validated_input(
    "Prix minimum de consultation",
    "0",
    validate_number,
    0,  # min_val
    MAX_PRICE  # max_val
)

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
    
    # Un seul défilement au début pour charger tous les éléments
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)  # Attente un peu plus longue pour s'assurer que tout est chargé
    
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
                date_text = availableDate.text.split('Prochain RDV le')[1].strip()
                
                # Vérification que le texte de la date est bien formaté
                if not date_text or len(date_text.split()) != 3:
                    print(f"DEBUG: Format de date invalide: {date_text}")
                    continue
                
                # Construction de la date au format JJ/MM/AAAA
                day = date_text.split(' ')[0]
                month = convert_month(date_text.split(' ')[1])
                year = date_text.split(' ')[2]
                date_str = f"{day}/{month}/{year}"
                
                print(f"DEBUG: Date extraite: {date_str}")
                
                # Conversion des dates en objets datetime pour la comparaison
                try:
                    appointment_date = None
                    start_date = None
                    end_date = None
                    if isinstance(date_str, datetime):
                        appointment_date = date_str
                    else:
                        appointment_date = datetime.strptime(date_str, "%d/%m/%Y")
                    print(f"DEBUG: Date du rendez-vous: {appointment_date.strftime('%d/%m/%Y')}")
                    if isinstance(START_DATE, datetime):
                        start_date = START_DATE
                    else:
                        start_date = datetime.strptime(START_DATE, "%d/%m/%Y")
                    print(f"DEBUG: Date de début: {start_date.strftime('%d/%m/%Y')}")
                    if isinstance(END_DATE, datetime):
                        end_date = END_DATE
                    else:
                        end_date = datetime.strptime(END_DATE, "%d/%m/%Y")
                    print(f"DEBUG: Date de fin: {end_date.strftime('%d/%m/%Y')}")
                    
                    print(f"DEBUG: Date du rendez-vous: {appointment_date.strftime('%d/%m/%Y')}")
                    print(f"DEBUG: Plage de dates: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
                    
                    # Vérification si la date est dans la plage de dates
                    if start_date <= appointment_date <= end_date:
                        try:
                            doctor_info['next_appointment'] = None 

                            # Clic sur le bouton de rendez-vous
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
                                    doctor_info['next_appointment'] = f"{date_str} {time_text}"
                                    break 
                                except Exception as e:
                                    print(f"DEBUG: Erreur lors de la lecture des horaires : {e}")
                                    continue
                        except Exception as e:
                            print(f"DEBUG: Erreur lors du traitement du docteur : {e}")
                    else:
                        print(f"DEBUG: Date hors plage ({date_str}), passage au médecin suivant")
                        continue
                except ValueError as e:
                    print(f"DEBUG: Erreur de conversion de date: {e}")
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
        time.sleep(1)

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
            time.sleep(1)
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
                time.sleep(1)

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
                    
                time.sleep(1)
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
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for doctor in availableDoctors:
            doctor_data = doctor.copy()
            
            # Nettoyage et formatage des données
            if isinstance(doctor_data.get('prices'), list):
                # Formatage des prix pour plus de lisibilité
                formatted_prices = []
                for price in doctor_data['prices']:
                    if '€' in price:
                        formatted_prices.append(price.strip())
                doctor_data['prices'] = ' | '.join(formatted_prices)
            elif doctor_data.get('prices') is None:
                doctor_data['prices'] = "Non communiqués"
                
            # Nettoyage de l'adresse
            if doctor_data.get('address'):
                # Suppression des doublons de secteur dans l'adresse
                address = doctor_data['address']
                if doctor_data.get('sector') and doctor_data['sector'] in address:
                    address = address.replace(doctor_data['sector'], '').strip()
                doctor_data['address'] = address
                
            # Nettoyage du type de consultation
            if not doctor_data.get('consultation_type'):
                doctor_data['consultation_type'] = "Présentiel"
                
            # Nettoyage du rendez-vous
            if not doctor_data.get('next_appointment'):
                doctor_data['next_appointment'] = "Non disponible"
                
            # S'assurer que tous les champs sont présents
            for field in fieldnames:
                if field not in doctor_data or doctor_data[field] is None:
                    doctor_data[field] = ""
                    
            writer.writerow(doctor_data)
            
    print("\nLes résultats ont été exportés dans docteurs.csv")
    print(f"Nombre de médecins exportés : {len(availableDoctors)}")
    
except Exception as e:
    print(f"Erreur dans la boucle principale : {e}")
finally:
    driver.quit()
