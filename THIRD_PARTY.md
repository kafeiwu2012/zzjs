# 第三方组件说明

本项目通过包管理器获取依赖，不将工具链或全部依赖缓存纳入源码ZIP。重建需要遵守对应上游许可证。

- FastAPI、Uvicorn：见各自官方仓库和发行包许可证。
- Eclipse Paho MQTT Python：见Eclipse Paho发行包许可证。
- AsyncMqttClient 0.9.0、AsyncTCP 1.1.1、ESPAsyncTCP 1.2.2：见对应库上游及arduino/libraries内许可证；AsyncTCP/ESPAsyncTCP使用LGPL系列许可证。交付固件包含其链接代码，重建所需本项目源码、精确版本及构建配置一并提供。
- ArduinoJson 6.21.5、Adafruit DHT 1.4.6、Adafruit Unified Sensor 1.1.15：见对应发行包许可证。
- Espressif Arduino核心及ESP8266 Arduino核心：通过Arduino开发板管理器获取；本版分别锁定esp32 2.0.17与esp8266 3.1.2，见各上游许可证。
- Android SDK及JDK：构建工具不打入项目包，按官方许可安装。
- Windows程序运行依赖系统Microsoft Edge；Edge不包含在本项目中。

测试代理Mosquitto和Zig交叉工具链仅用于当前环境验证，不打入运行交付包。实际树莓派通过系统包管理器安装Mosquitto。
