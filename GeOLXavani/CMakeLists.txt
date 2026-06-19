cmake_minimum_required(VERSION 3.16)

project(GeOLXavani VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17) # Ensure modern C++ features are active
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 1. CHANGE: Find Widgets module instead of Quick/QML
find_package(Qt6 REQUIRED COMPONENTS Widgets)

qt_standard_project_setup(REQUIRES 6.10)

# Enable Qt's Meta-Object Compiler (Required for C++ Slots and Signals)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# 2. CHANGE: Added all of your C++ app files cleanly into the executable definition
qt_add_executable(appGeOLXavani
    main.cpp
    MainWindow.h
    MainWindow.cpp
    ScraperWidget.h
    ScraperWidget.cpp
    MlWidget.h
    MlWidget.cpp
    TrainingWidget.h
    TrainingWidget.cpp
    CarSearchWidget.h
    CarSearchWidget.cpp
    CarEvaluationWidget.h
    CarEvaluationWidget.cpp
)

# 3. DELETED: The old "qt_add_qml_module" block because you do not need
# Main.qml to serve as your UI anymore—MainWindow.cpp is building everything natively.

set_target_properties(appGeOLXavani PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

# 4. CHANGE: Link to Qt6::Widgets instead of Qt6::Quick
target_link_libraries(appGeOLXavani
    PRIVATE Qt6::Widgets
)

# Add your python script to the project tree view
add_custom_target(PythonScripts SOURCES
    olx_car_scraper.py
    ml-training.py
)

install(TARGETS appGeOLXavani
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Add this right below your project(GeOLXavani ...) lines in CMakeLists.txt
target_compile_definitions(appGeOLXavani PRIVATE PROJECT_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")