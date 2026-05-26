#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QStackedWidget>
#include <QWidget>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QProcess>

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    // Navigation slots
    void showMainMenu();
    void showTrainModelView();
    void showCheckValueView();

    // Action slots
    void runWebScraper();
    void handleTrainModel();
    void handleCheckPrice();

private:
    QStackedWidget *stackedWidget;

    // View Widgets
    QWidget *mainMenuWidget;
    QWidget *trainModelWidget;
    QWidget *checkValueWidget;

    // Check Value Input Fields (for later ML integration)
    QLineEdit *brandInput;
    QLineEdit *modelInput;
    QLineEdit *yearInput;
    QLineEdit *kmInput;
    QLabel *priceResultLabel;

    // Train Model Input Fields
    QLineEdit *datasetPathInput;

    void createMainMenu();
    void createTrainModelView();
    void createCheckValueView();
};

#endif // MAINWINDOW_H