#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QTimer>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("Sonora"));
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.0"));
    QCoreApplication::setOrganizationName(QStringLiteral("Sonora"));

    QQmlApplicationEngine engine;
    const QUrl mainUrl(QStringLiteral("qrc:/qt/qml/Sonora/qml/Main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, [] { QCoreApplication::exit(EXIT_FAILURE); },
                     Qt::QueuedConnection);
    engine.load(mainUrl);

    if (QCoreApplication::arguments().contains(QStringLiteral("--smoke-test")))
        QTimer::singleShot(1200, &app, &QCoreApplication::quit);

    return app.exec();
}
