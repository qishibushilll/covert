from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("测试浏览器初始化...")

try:
    # 浏览器选项配置
    options = webdriver.ChromeOptions()
    
    # 反检测配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # 性能和稳定性配置
    options.add_argument('--start-maximized')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    
    # 直接启动Chrome，不使用ChromeDriverManager
    print("尝试直接启动Chrome...")
    driver = webdriver.Chrome(options=options)
    print("浏览器启动成功！")
    driver.quit()
    print("浏览器已关闭")
except Exception as e:
    print(f"直接启动失败: {e}")
    
    try:
        print("尝试使用ChromeDriverManager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("浏览器启动成功！")
        driver.quit()
        print("浏览器已关闭")
    except Exception as e2:
        print(f"ChromeDriverManager启动失败: {e2}")
        print("请确保已安装Chrome浏览器和对应版本的ChromeDriver")

