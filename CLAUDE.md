# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains ECU tuning maps and base configurations for Classic Mini automotive ECU systems. It serves as a public record of base maps for various ECU platforms, created to help Classic Mini enthusiasts get a starting point for their own engine tuning projects.

## Repository Structure

The repository is organized by ECU platform manufacturer:

- **Haltech/**: Haltech ECU maps and configurations
  - `E550/`, `E750/`, `R3/`: Model-specific configurations
  - `Reference Maps/`: Baseline reference configurations
  - `Sensor Scales/`: Sensor calibration data
  - `Wiring Diagrams/`: Electrical connection diagrams
- **Speeduino-Megasquirt/**: Open-source ECU platform maps (.msq files)
- **Emerald/**: Emerald ECU configurations (.map files)
- **DTAFast - Ignition Only/**: DTA Fast ignition-only configurations
- **ECUMaster/**: ECUMaster platform configurations (work in progress)
- **MaxxECU/**: MaxxECU platform configurations (work in progress)
- **MegaJolt - Ignition Only/**: MegaJolt ignition system configurations
- **diagrams/**: Technical wiring and component diagrams organized by component type (created using WireViz)

## File Types and Formats

- `.msq`: MegaSquirt/Speeduino tuning files
- `.map`: Generic ECU map files (Emerald, DTA Fast)
- `.htf`: Haltech tuning files (not present in current structure)
- Wiring diagrams and technical documentation in various formats

## Important Safety Information

**CRITICAL**: All maps in this repository are base configurations and are **NOT PLUG AND PLAY**. They require professional dyno tuning and proper vehicle-specific configuration before use. Using these maps without proper tuning can result in catastrophic engine failure.

## Development Workflow

This is primarily a documentation and configuration repository for automotive ECU tuning. Changes should be carefully tracked as they represent real-world engine tuning data that affects vehicle safety and performance.

### Wiring Diagram Creation

Wiring diagrams in the `/diagrams` folder are created using WireViz, a tool for generating wiring harness documentation from YAML configuration files. WireViz produces both visual diagrams and bill of materials (BOM) for electrical connections.

## Platform Support Matrix

The repository supports multiple ECU platforms with varying feature completeness:
- Haltech: Full feature support (ignition, fuel, VE tables, boost control, drive-by-wire)
- Speeduino/MegaSquirt: Partial support (ignition and fuel maps)
- Emerald: Basic support (ignition and fuel maps)
- DTAFast/MegaJolt: Ignition-only configurations
- ECUMaster/MaxxECU: Work in progress

## File Organization

Maps are organized by ECU platform and further subdivided by engine configuration (standard vs 16V variants). Each platform directory contains the base maps along with supporting documentation like wiring diagrams and sensor calibrations where applicable.