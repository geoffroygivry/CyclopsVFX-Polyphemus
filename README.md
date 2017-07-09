# README #

## Welcome to CyclopsVFX Polyphemus! ##

[![Build Status](https://travis-ci.org/geoffroygivry/CyclopsVFX-Polyphemus.svg?branch=master)](https://travis-ci.org/geoffroygivry/CyclopsVFX-Polyphemus.svg?branch=master)

### A beta release is scheduled for Sept/Oct 2017. At the meantime, if you have any questions, please open an issue and I'll reply ASAP. Contributors are more than welcome if you are interested in the project. Thank you! ###

**CyclopsVFX**, is an Open Source Production Tracking Software and pipeline toolkit, for your **VFX, Video Game and Animation pipeline**. CyclopsVFX has 2 main Frameworks : **Unity** and **Polyphemus**.

**Unity** is the framework that connects programs such as **Nuke, Maya, Mari, Clarisse IFX** together. It is mostly written in **python** and uses popular libraries like **PySide** and **PyQt4**.

**Polyphemus** is the Web Application that goes with **Unity**. It centralise information and data. It uses a **MongoDB** Database to store securely your data and uses popular web frameworks like **Flask, JQuery, AngularJS and Rabbitmq and Celery** other many more modern tools.

#### Roadmap ####

The Sept/Oct Beta Version is aiming of:

- Having a fully working web app (Polyphemus) working flawlessly with the python framework (Unity) for Maya and Nuke. ClarisseIFX and Houdini will come later.
- Having simple but full featured publishing system.
- Having a Dailies submission system.
- having a basic API.
- Having a documentation.
- having video tutorials for getting started with CyclopsVFX, step by step installation and short videos of using both Polyphemus and Unity.
- Unity will work on Linux (CentOS, Fedora and Ubuntu) and Windows10. OSX will come shortly after this release as it needs further unit testing.
