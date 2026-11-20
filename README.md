# door-tracker-and-server


Initial Draft of code by Google Gemini

## Notes from the Robot

### **Pin Out Mapping Table**
| Component | Component Pin | Raspberry Pi 5 Pin | BCM GPIO Pin | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **HC-SR04** | VCC | Pin 2 | **5V Power** | Sensor power |
| | GND | Pin 6 | **Ground** | Common ground |
| | Trig | Pin 13 | **GPIO 27** | Distance trigger |
| | Echo | Pin 11 | **GPIO 17** | **Via voltage divider (3.3V)** |
| **Door LED** | Anode (+) | Pin 12 | **GPIO 18** | Via \\(220\Omega\\) resistor |
| | Cathode (-) | Pin 14 | **Ground** | Ground |
| **Push Button**| Pin A | Pin 15 | **GPIO 22** | Baseline calibration button |
| | Pin B | Pin 20 | **Ground** | Ground |

### **Voltage Divider Diagram for Echo Pin**
\\[\text{Echo (HC-SR04)} \longrightarrow [1\text{ k}\Omega] \longrightarrow \text{GPIO 17 (Pin 11)} \longrightarrow [2\text{ k}\Omega] \longrightarrow \text{GND (Pin 6)}\\]

## Todo

[] Secure Web Server
[] Malicious Door Opening Detection?
[] Video Demo
[] Report?
