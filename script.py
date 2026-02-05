import time
import sys
import os
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
#               НАСТРОЙКИ
# ==========================================

PROFILE_PATH = os.path.join(os.getcwd(), "chrome_profile")
URL_MENU = "https://urfu.modeus.org/learning-path-selection/menus"
CAMPAIGN_NAME = "Выбор ИРИТ-РТФ 3 курс 6 семестр (2025-2026 уч.г.) Набор 2023г."

TARGETS = [
    {
        "category": "Моделирование сложных процессов и систем",
        "course": "Моделирование сложных вероятностных систем",
        "groups": ["ПА-07", "Л-01"] 
    }
]

# ==========================================
#           СЛУЖЕБНЫЕ ФУНКЦИИ
# ==========================================

def init_driver():
    """Запуск браузера (Режим Detach - не закрывается сам)"""
    print("\n[SYSTEM] Запуск Chrome...")
    options = Options()
    
    # Пути к Chrome
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    binary_path = None
    for path in possible_paths:
        if os.path.exists(path):
            binary_path = path
            break
    if binary_path: options.binary_location = binary_path

    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--remote-debugging-port=9222") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.page_load_strategy = 'eager'
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    
    options.add_experimental_option("detach", True) 

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"\n[FATAL] Ошибка драйвера: {e}")
        input("Нажми Enter...")
        sys.exit(1)

# ==========================================
#        ТУРБО-КЛИКИ И ПОИСК
# ==========================================

def click_confirm_button(driver):
    xpath_btn = "//button[contains(@class, 'p-button-success') and .//span[contains(text(), 'Выбрать')]]"
    try:
        btn = WebDriverWait(driver, 1, poll_frequency=0.1).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
        driver.execute_script("arguments[0].click();", btn)
        print("      [>>>] КНОПКА 'ВЫБРАТЬ' НАЖАТА!")
        return True
    except:
        return False

def open_category_tree(driver, category_name):
    cat_clean = category_name.strip()
    xpath_row = f"//tr[contains(@class, 'root')]//div[contains(@class, 'name') and contains(text(), '{cat_clean}')]/ancestor::tr"
    try:
        rows = driver.find_elements(By.XPATH, xpath_row)
        if not rows: return False
        row = rows[0]
        if len(row.find_elements(By.CSS_SELECTOR, "chevronrighticon")) > 0:
            btn = row.find_element(By.CSS_SELECTOR, "p-treetabletoggler button")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.1) 
        return True
    except: return False

def find_and_click_course(driver, course_name):
    course_clean = course_name.strip()
    xpath = f"//tr[not(contains(@class, 'root'))]//div[contains(@class, 'name') and contains(text(), '{course_clean}')]"
    try:
        elems = driver.find_elements(By.XPATH, xpath)
        if elems:
            if not elems[0].is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elems[0])
            driver.execute_script("arguments[0].click();", elems[0])
            return True
        return False
    except: return False

def ensure_campaign(driver, wait):
    if len(driver.find_elements(By.TAG_NAME, "p-treetable")) > 0: return True
    xpath = f"//span[contains(text(), '{CAMPAIGN_NAME}')]"
    try:
        elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        elem.click()
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "p-treetable")))
        return True
    except: return False

# ==========================================
#           ФУНКЦИЯ БОЕВОГО ЦИКЛА
# ==========================================

def run_automation_cycle(driver, wait):
    print("\n[START] Скрипт работает. (Для остановки жми Ctrl+C в консоли)")
    
    for t in TARGETS: t['done'] = False
    
    try:
        while True:
            ensure_campaign(driver, wait)

            all_done = True
            for item in TARGETS:
                if item['done']: continue
                all_done = False
                
                cat = item['category']
                course = item['course']
                
                if not open_category_tree(driver, cat): continue
                if not find_and_click_course(driver, course): continue

                try:
                    WebDriverWait(driver, 2, poll_frequency=0.1).until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-module-card")))
                    
                    if len(driver.find_elements(By.CSS_SELECTOR, "app-module-card p-dropdown")) == 0:
                        try: driver.find_element(By.CSS_SELECTOR, ".card-header").click()
                        except: pass
                        continue

                    dropdowns = driver.find_elements(By.CSS_SELECTOR, "app-module-card p-dropdown")
                    is_selected = False

                    for target in item['groups']:
                        if is_selected: break
                        for dd in dropdowns:
                            try:
                                trig = dd.find_element(By.CSS_SELECTOR, ".p-dropdown-trigger")
                                driver.execute_script("arguments[0].click();", trig)
                                
                                WebDriverWait(driver, 0.3, poll_frequency=0.05).until(
                                    EC.visibility_of_element_located((By.CSS_SELECTOR, "li.p-dropdown-item"))
                                )
                                
                                item_xpath = f"//li[contains(@class, 'p-dropdown-item')]//span[contains(text(), '{target}')]"
                                opts = driver.find_elements(By.XPATH, item_xpath)
                                
                                if opts and opts[0].is_displayed():
                                    opts[0].click()
                                    if click_confirm_button(driver):
                                        is_selected = True
                                        break
                            except: pass
                    
                    if is_selected:
                        print(f"   [ГОТОВО] {course} - УСПЕХ!")
                        item['done'] = True
                    
                    try: driver.find_element(By.CSS_SELECTOR, ".card-header").click()
                    except: pass
                    
                except Exception:
                    try: driver.find_element(By.CSS_SELECTOR, ".card-header").click()
                    except: pass

            if all_done:
                print("\n>>> ЗАДАЧА ВЫПОЛНЕНА! <<<")
                return

    except KeyboardInterrupt:
        print("\n[PAUSE] Скрипт остановлен. Браузер работает.")
        return

# ==========================================
#           ГЛАВНОЕ МЕНЮ
# ==========================================

def main_menu():
    driver = init_driver()
    wait = WebDriverWait(driver, 3, poll_frequency=0.1)

    try:
        driver.get(URL_MENU)
        print("\n" + "="*50)
        print("   БРАУЗЕР ЗАПУЩЕН")
        print("="*50)

        while True:
            print("\nНажми [ENTER], чтобы запустить перебор предметов.")
            print("(Чтобы остановить перебор, нажми Ctrl+C, но браузер останется)")
            
            input(">>> Жду команды... ")
            
            run_automation_cycle(driver, wait)

    except Exception as e:
        print(f"\n[CRASH] {e}")

if __name__ == "__main__":
    main_menu()