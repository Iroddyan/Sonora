#include <QGuiApplication>
#include <QFont>
#include <QFontDatabase>
#include <QDir>
#include <QDebug>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QStandardPaths>
#include <QTimer>

#include "library/LibraryService.h"
#include "playback/PlaybackService.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QFontDatabase::addApplicationFont(QStringLiteral(":/sonora/assets/fonts/MaterialIcons-Regular.ttf"));
    app.setFont(QFont(QStringLiteral("Noto Sans"), 10));
    QCoreApplication::setApplicationName(QStringLiteral("Sonora"));
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.0"));
    QCoreApplication::setOrganizationName(QStringLiteral("Sonora"));

    const bool smokeTest = QCoreApplication::arguments().contains(QStringLiteral("--smoke-test"));
    if (smokeTest)
        QStandardPaths::setTestModeEnabled(true);
    const QString dataDirectory = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir().mkpath(dataDirectory);
    Sonora::LibraryService library(dataDirectory + QStringLiteral("/library.sqlite"));
    Sonora::PlaybackService playback(library.tracks());

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("Library"), &library);
    engine.rootContext()->setContextProperty(QStringLiteral("Playback"), &playback);
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
