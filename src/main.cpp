#include <QGuiApplication>
#include <QDir>
#include <QDebug>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QStandardPaths>
#include <QTimer>

#include "library/LibraryService.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("Sonora"));
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.0"));
    QCoreApplication::setOrganizationName(QStringLiteral("Sonora"));

    const bool smokeTest = QCoreApplication::arguments().contains(QStringLiteral("--smoke-test"));
    if (smokeTest)
        QStandardPaths::setTestModeEnabled(true);
    const QString dataDirectory = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir().mkpath(dataDirectory);
    Sonora::LibraryService library(dataDirectory + QStringLiteral("/library.sqlite"));

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("Library"), &library);
    const QUrl mainUrl(QStringLiteral("qrc:/qt/qml/Sonora/qml/Main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, [] { QCoreApplication::exit(EXIT_FAILURE); },
                     Qt::QueuedConnection);
    QObject::connect(&engine, &QQmlApplicationEngine::warnings, &app,
                     [](const QList<QQmlError> &warnings) {
                         for (const QQmlError &warning : warnings)
                             qWarning().noquote() << warning.toString();
                     });
    engine.load(mainUrl);

    if (smokeTest)
        QTimer::singleShot(1200, &app, &QCoreApplication::quit);

    return app.exec();
}
