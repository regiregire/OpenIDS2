OpenIDS2: Open-source Inkjet DNA Synthesizer (2nd Gen)
OpenIDS2 is a low-cost, high-precision, open-source hardware platform designed for the reproducible construction of DNA microarray synthesizers. Developed at the Synthetic Biology Laboratory (Bang Lab) at Yonsei University, this second-generation system significantly improves upon the original OpenIDS by reducing the device volume by two-thirds, integrating all electronics into a custom PCB, and enhancing operational stability through a peristaltic pump-based fluidics system.

This project serves as a foundational step toward the "Bio-Dark Factory"—an fully automated, human-free biological experimental platform.

🔗 Publication
Title: OpenIDS2: A low-cost, 3D-printed, open-source platform for reproducible construction of DNA microarray synthesizers

Journal: PLOS ONE (2025)

DOI: 10.1371/journal.pone.0338478

✨ Key Features
Accessibility: Most mechanical components are designed for 3D printing (PLA/Resin), allowing for low-cost fabrication and assembly.

Compact Design: Optimized for laboratory benchtop use with a significantly reduced footprint compared to the 1st generation.

Reliable Fluidics: Utilizes a peristaltic pump system for bulk solution delivery, improving maintenance and reproducibility.

Integrated Control: A custom-designed PCB manages power distribution, motor drivers, and sensor inputs to eliminate complex wiring.

Automated Workflow: Python-based GUI allows users to control the entire synthesis cycle—from sequence design to final oxidation.

📂 Repository Structure
Arduino/: Firmware for Master and Slave microcontrollers managing motion and printhead control.

Hardware/: 3D design files (.f3d), circuit schematics, and a detailed Bill of Materials (BOM).

Python/: PyQt5-based GUI application for system operation and sequence management.

Data/: Example DNA sequences and synthesis protocols.
