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

class ScraperWidget : public QWidget
{
    Q_OBJECT

public:
    explicit ScraperWidget(QWidget *parent = nullptr);
    ~ScraperWidget();

signals:
    void backToMainMenuRequested(); // Let the main window know we want to go back

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