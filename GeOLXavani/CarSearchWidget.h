#ifndef CARSEARCHWIDGET_H
#define CARSEARCHWIDGET_H

#include <QWidget>
#include <QTableView>
#include <QStandardItemModel>
#include <QLineEdit>
#include <QPushButton>
#include <QComboBox>

class CarSearchWidget : public QWidget
{
    Q_OBJECT

public:
    explicit CarSearchWidget(QWidget *parent = nullptr);
    ~CarSearchWidget();
    void loadDataset();

signals:
    void backToTrainingRequested();

private slots:
    void onSearchClicked();

private:
    void setupUi();
    void filterTable();

    QTableView *resultsTableView;
    QStandardItemModel *tableModel;
    QLineEdit *searchLineEdit;
    QComboBox *searchFieldCombo;
    QPushButton *searchButton;
    QPushButton *backButton;

    QList<QStringList> originalData;
    QStringList headers;
};

#endif // CARSEARCHWIDGET_H