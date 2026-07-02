#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>

#define PIR_PIN 13

// WIFI
const char* ssid = "[SSID]";
const char* password = "[PASSWORD]";

// MQTT
const char* mqtt_server = "[SERVER]";
const int mqtt_port = 1883;

const char* mqtt_user = "[USER]";
const char* mqtt_pass = "[PASSWORD]";

WiFiClient espClient;
PubSubClient client(espClient);

bool lastState = false;

void setup_wifi() {

    Serial.print("Connecting to WiFi");

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi OK");
}

void reconnect() {

    while (!client.connected()) {

        Serial.print("Connecting to MQTT...");

        String clientId = "ESP32-PIR-";
        clientId += String(random(0xffff), HEX);

        if (client.connect(
                clientId.c_str(),
                mqtt_user,
                mqtt_pass)) {

            Serial.println("OK");

        } else {

            Serial.print("Error=");
            Serial.println(client.state());

            delay(5000);
        }
    }
}

void setup() {

    Serial.begin(115200);

    pinMode(PIR_PIN, INPUT);

    setup_wifi();

    client.setServer(mqtt_server, mqtt_port);

    Serial.println("System is ready");
}

void loop() {

    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    bool motion = digitalRead(PIR_PIN);

    if (motion != lastState) {

        if (motion) {

            Serial.println("MOTION");

            client.publish(
                "esp32/pir/status",
                "motion_detected"
            );

        } else {

            Serial.println("NO MOTION");

            client.publish(
                "esp32/pir/status",
                "no_motion"
            );
        }

        lastState = motion;
    }

    delay(100);
}