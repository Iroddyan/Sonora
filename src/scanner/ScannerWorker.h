#pragma once

#include "../library/Track.h"

#include <QObject>
#include <memory>
#include <atomic>

namespace Sonora {

class ScannerWorker final : public QObject {
    Q_OBJECT

public:
    ScannerWorker(QStringList roots, std::shared_ptr<std::atomic_bool> cancelled);

public slots:
    void scan();

signals:
    void progressChanged(int scannedAudioFiles);
    void completed(const Sonora::ScanResult &result);

private:
    QStringList m_roots;
    std::shared_ptr<std::atomic_bool> m_cancelled;
};

} // namespace Sonora
