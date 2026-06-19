#ifndef SCRAPERWIDGET_H
#define SCRAPERWIDGET_H

#include <QWidget>
#include <QLineEdit>
#include <QSpinBox>
#include <QCheckBox>
#include <QPushButton>
#include <QTableView>
#include <QStandardItemModel>
#include <QProcess>

// Forward Declaration para quebrar a dependência circular
class MainWindow;

class ScraperWidget : public QWidget
{
    Q_OBJECT

public:
    // Mantendo a assinatura exata que usas no teu projeto
    explicit ScraperWidget(QWidget *parent = nullptr);
    ~ScraperWidget();

signals:
    void backToMainMenuRequested();

private slots:
    void onRunScraperClicked();
    void onScraperFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void readScraperOutput();

private:
    void setupUi();
    void loadCsvToTable(const QString &filePath);

    QLineEdit *brandInput;
    QSpinBox *pagesSpinBox;
    QSpinBox *priceMinSpinBox;
    QSpinBox *priceMaxSpinBox;
    QSpinBox *yearMinSpinBox;
    QSpinBox *yearMaxSpinBox;
    QCheckBox *detailCheckBox;
    QCheckBox *showBrowserCheckBox;
    QPushButton *runButton;
    QPushButton *backButton;

    QTableView *resultsTableView;
    QStandardItemModel *tableModel;
    QProcess *scraperProcess;
    QString expectedCsvPath;
};

#endif // SCRAPERWIDGET_H