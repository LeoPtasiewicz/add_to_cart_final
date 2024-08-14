import undetected_chromedriver as uc
import time
import dotenv
import os
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import random
import pandas as pd
import ast
import sys
from selenium.common.exceptions import StaleElementReferenceException
import pyautogui

chrome_options = uc.ChromeOptions()
prefs = {
    'credentials_enable_service': False,
    'profile.password_manager_enabled': False
}
chrome_options.add_experimental_option('prefs', prefs)
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")

driver = uc.Chrome(options=chrome_options)

def wait_for_non_empty_text(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(
        lambda d: d.find_element(*locator).text.strip(),
        f"Element with locator {locator} did not have non-empty text after {timeout} seconds"
    )

def send_keys_slowly(field, text):
    for char in text:
        field.send_keys(char)
        time.sleep(random.uniform(0.1, 0.5))


def login():
    env_file = '.env.beta' if '--beta' in sys.argv else '.env'
    load_dotenv(env_file)
    username = os.getenv('MY_USERNAME')
    password = os.getenv('MY_PASSWORD')

    driver.get("https://www.tcgplayer.com/login")

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'Email')))

    # Wait for 2 seconds after page load
    time.sleep(2)
    driver.maximize_window()


    # Find the username and password fields and the login button
    username_field = driver.find_element(By.NAME, 'Email')
    password_field = driver.find_element(By.NAME, 'Password')
    login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')

    send_keys_slowly(username_field, username)
    time.sleep(.5)
    for _ in range(2):
        pyautogui.hotkey('alt', 'tab')
        time.sleep(2)
    send_keys_slowly(password_field, password)
    time.sleep(1)

    # Click login button
    login_button.click()

    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.marketplace-footer__address.align-self-center')))

    time.sleep(5)

    # print("Please complete any additional verification if prompted. Type 'ok' in the terminal to continue.")
    # while input().strip().lower() != 'ok':
    #     print("Please type 'ok' to continue after logging in.")

# ---------------------------------------------------------------- #

def safe_literal_eval(val):
    if isinstance(val, str):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return []
    return val

def join_exports():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    export_path = os.path.join(script_dir, 'exports', 'export.csv')
    reference_path = os.path.join(script_dir, 'exports', 'reference_file.csv')
    
    # Read CSV files
    export_df = pd.read_csv(export_path)
    reference_df = pd.read_csv(reference_path, usecols=['prizeid', 'new_url'])

    # Convert Allprizeids to list
    export_df['Allprizeids'] = export_df['Allprizeids'].apply(safe_literal_eval)

    # Function to find matching new_url
    def find_matching_url(allprizeids):
        matching_urls = reference_df[reference_df['prizeid'].isin(allprizeids)]['new_url'].dropna().tolist()
        return matching_urls[0] if matching_urls else ''

    # Apply the function to get matching new_url
    export_df['matching_new_url'] = export_df['Allprizeids'].apply(find_matching_url)

    # Save the result
    output_path = os.path.join(script_dir, 'exports', 'combined_order_details.csv')
    export_df.to_csv(output_path, index=False)
    print(f"Output saved as: {output_path}")

    # Print some statistics
    print(f"Total rows in export_df: {len(export_df)}")
    print(f"Rows with matching new_url: {(export_df['matching_new_url'] != '').sum()}")
    print(f"Rows without matching new_url: {(export_df['matching_new_url'] == '').sum()}")
    combined_df = pd.read_csv(output_path)
    filtered_df = export_df[export_df['matching_new_url'] == '']
    for index, row in filtered_df.iterrows():
        print(f"Name: {row['Name']}, Game name: {row['Game name']}")

    aggregated_output_file = os.path.join(script_dir, 'exports', 'aggregated_order_details.csv')

    if os.path.exists(aggregated_output_file):
        os.remove(aggregated_output_file)
        print(f"Deleted existing file: {aggregated_output_file}")

    # Aggregate data to get unique URLs and their corresponding quantities
    aggregated_df = combined_df.groupby(['matching_new_url', 'Name']).size().reset_index(name='Quantity')
    aggregated_df = aggregated_df.sort_values('Quantity', ascending=False)

    # Save the aggregated data to a new CSV file
    aggregated_df.to_csv(aggregated_output_file, index=False)
    print(f"Aggregated data saved to {aggregated_output_file}")

# -------------------------------------------------------------------- #

def gather_listings(card_url, page):
    listings_data = []
    try:
        # Update the URL with the appropriate page number before navigating
        if '&page=' in card_url:
            card_url = card_url.replace(f'&page={page-1}', f'&page={page}')
        else:
            card_url = f"{card_url}&page={page}"
        
        driver.get(card_url)

        time.sleep(1)

        # Wait for the 'Add to Cart' buttons to be present
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.tcg-standard-button__content')))

        time.sleep(.1)

        # Wait for the listings to be present and log the number found
        listing_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.listing-item__listing-data'))
        )
        time.sleep(1)
        print(f"Number of listing elements found: {len(listing_elements)}")



        # Find the listings again and compare the count
        listings = driver.find_elements(By.CSS_SELECTOR, '.listing-item__listing-data')
        print(f"Number of listings after delay: {len(listings)}")

        for index, listing in enumerate(listings):
            try:
                available_quantity_element = listing.find_element(By.CSS_SELECTOR, '.add-to-cart__available')
                available_quantity_text = available_quantity_element.text.strip().split()[-1]
                available_quantity = int(available_quantity_text)
                add_to_cart_button = listing.find_element(By.CSS_SELECTOR, '.add-to-cart__wrapped__submit')
                listings_data.append((add_to_cart_button, available_quantity))
            except StaleElementReferenceException:
                print(f"Stale element encountered for listing at index {index}")
            except NoSuchElementException:
                print(f"Element not found for listing at index {index}")

    except TimeoutException as e:
        print(f"Timeout occurred while gathering listings: {e}")

    print(f"Total listings data gathered: {len(listings_data)}")
    return listings_data


def add_card_to_cart(card_name, card_url, desired_quantity):
    total_added = 0
    order_summary = []
    current_page = 1

    while total_added < desired_quantity:
        listings_data = gather_listings(card_url, page=current_page)
        

        if not listings_data:
            break  # No more listings available, stop the loop

        added_in_this_page = 0

        for index, (add_to_cart_button, available_quantity) in enumerate(listings_data):
            if total_added >= desired_quantity:
                break

            while available_quantity > 0 and total_added < desired_quantity:
                try:
                    time.sleep(1)
                    WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable(add_to_cart_button)
                    )
                    
                    add_to_cart_button.click()
                    time.sleep(2)  # Small delay to ensure the action is processed

                    # Check for popup after attempting to add to cart
                    if is_popup_present():
                        print("Popup detected after attempting to add to cart.")
                        time.sleep(2)  # Wait for 2 seconds
                        try:
                            okay_button = driver.find_element(By.CSS_SELECTOR, '.modal__close')
                            okay_button.click()
                            time.sleep(1)  # Small delay to ensure the action is processed
                            print("Clicked 'Okay' button on popup.")
                            break  # Skip to the next listing
                        except (NoSuchElementException, TimeoutException) as popup_e:
                            print(f"Error clicking 'Okay' button: {popup_e}")
                            break  # Skip to the next listing
                    else:
                        total_added += 1
                        added_in_this_page += 1
                        available_quantity -= 1
                        print(f"Added 1 of {card_name} to cart.")
                
                except (ElementClickInterceptedException, ElementNotInteractableException) as e:
                    print(f"Error clicking add to cart button: {e}")
                    if is_popup_present():
                        print("Popup detected while attempting to add to cart.")
                        time.sleep(2)  # Wait for 2 seconds
                        try:
                            okay_button = driver.find_element(By.CSS_SELECTOR, '.add-item-error__action__primary-btn')
                            okay_button.click()
                            time.sleep(1)  # Small delay to ensure the action is processed
                            print("Clicked 'Okay' button on popup.")
                            break  # Skip to the next listing
                        except StaleElementReferenceException as e:
                            print(f"Stale element encountered in add_card_to_cart: {e}")
                            print("Element that became stale: add_to_cart_button")
                            break  # Move to the next listing
                        except (ElementClickInterceptedException, ElementNotInteractableException) as e:
                            print(f"Error clicking add to cart button: {e}")
                    else:
                        continue

        if added_in_this_page == 0:
            break  # If no items were added in this page, stop pagination

        current_page += 1

    if total_added < desired_quantity:
        print(f"Could not add the desired quantity of {card_name} to the cart. Added {total_added} out of {desired_quantity}.")
    
    order_summary.append((card_name, total_added))
    return order_summary, total_added


def is_popup_present():
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.add-item-error__action__primary-btn'))
        )
        return True
    except (NoSuchElementException, TimeoutException):
        return False

order_summary = []
unable_to_order = []

# def gather_listings():
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     aggregated_df = os.path.join(script_dir, 'exports', 'aggregated_order_details.csv')
#     df = pd.read_csv(aggregated_df)

#     try:
#         for index, row in df.iterrows():
#             card_url = row['matching_new_url']
#             driver.get(card_url)
#             time.sleep(4)
#             print(card_url)
#     finally:
#         driver.quit()



#     try:
#         # Update the URL with the appropriate page number before navigating
#         if '&page=' in card_url:
#             card_url = card_url.replace(f'&page={page-1}', f'&page={page}')
#         else:
#             card_url = f"{card_url}&page={page}"
        
#         # Navigate to the updated URL
#         driver.get(card_url)

#         WebDriverWait(driver, 20).until(
#             EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.listing-item__listing-data'))
#         )
#         WebDriverWait(driver, 20).until(
#             EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.tcg-standard-button__content')))
#         listings = driver.find_elements(By.CSS_SELECTOR, '.listing-item__listing-data')

#         for listing in listings:
#             try:
#                 available_quantity_element = listing.find_element(By.CSS_SELECTOR, '.add-to-cart__available')
#                 available_quantity_text = available_quantity_element.text.strip().split()[-1]
#                 available_quantity = int(available_quantity_text)
#                 add_to_cart_button = listing.find_element(By.CSS_SELECTOR, '.add-to-cart__wrapped__submit')
#                 listings_data.append((add_to_cart_button, available_quantity))
#             except NoSuchElementException:
#                 continue  # If any element is not found, move to the next listing

#     except TimeoutException as e:
#         print(f"An error occurred while gathering listings: {e}")

#     print(card_url)
#     return listings_data

# def print_card_url(card_url, page):
#     current_page = 1
#     try:
#         listings_data = gather_listings(card_url, page=current_page)
#         print(card_url)
#     finally:
#         print(card_url)



# join_exports()
# login()
# gather_listings()
# time.sleep(1)

# driver.quit()

try:
    join_exports()
    login()
    aggre_dir = os.path.dirname(os.path.abspath(__file__))
    aggre_path = os.path.join(aggre_dir, 'exports', 'aggregated_order_details.csv')
    df = pd.read_csv(aggre_path)

    # Iterate through each card URL and add to cart
    for index, row in df.iterrows():    
        card_url = row['matching_new_url']
        desired_quantity = row['Quantity']
        try:
            summary, added_quantity = add_card_to_cart(card_url.split('/')[-1], card_url, desired_quantity)
            order_summary.extend(summary)
            if added_quantity < desired_quantity:
                unable_to_order.append((card_url, desired_quantity - added_quantity))
        except Exception as e:
            print(f"An error occurred while processing {card_url}: {e}")
            unable_to_order.append((card_url, desired_quantity))
            continue  # Move to the next card

    print("All cards processed. The browser will remain open for manual actions.")
    print("\nOrder Summary:")
    for card, quantity in order_summary:
        print(f"Ordered {quantity} of {card}")

    if unable_to_order:
        print("\nUnable to Order:")
        for card_url, quantity in unable_to_order:
            print(f"Unable to order {quantity} of {card_url}")


except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Attempt to quit the driver properly
    try:
        driver.quit()
        print("Chrome WebDriver has been quit successfully.")
    except Exception as e:
        print(f"An error occurred while quitting the driver: {e}")
