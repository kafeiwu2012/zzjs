#pragma once
#include <Arduino.h>
#ifdef ESP32
#include <WiFi.h>

#include <Preferences.h>
#else
#include <ESP8266WiFi.h>

#include <LittleFS.h>
#endif
struct NetworkSettings {String ssid,password,server,code,mqttPassword,apPassword,id;};
extern NetworkSettings net;
void networkSetup();void networkLoop();void openPortal();

void networkMQTTReady();
