cmake_minimum_required(VERSION 3.24)
project(Sonora VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
include(CTest)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Qml Quick)
if(COMMAND qt_policy)
    qt_policy(SET QTP0004 NEW)
endif()
qt_standard_project_setup(REQUIRES 6.5)

qt_add_executable(sonora
    src/main.cpp
)

qt_add_qml_module(sonora
    URI Sonora
    VERSION 1.0
    QML_FILES
        qml/Main.qml
        qml/Theme.qml
        qml/components/NavButton.qml
        qml/components/EmptyPage.qml
)

target_link_libraries(sonora PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Quick)

install(TARGETS sonora RUNTIME DESTINATION bin)

if(BUILD_TESTING)
    add_test(NAME application_shell_smoke COMMAND sonora --smoke-test)
    set_tests_properties(application_shell_smoke PROPERTIES
        ENVIRONMENT "QT_QPA_PLATFORM=offscreen;QT_QUICK_BACKEND=software"
        TIMEOUT 10
    )
endif()
