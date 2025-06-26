from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import RoundedRectangle, Color, Rectangle, Rotate, PushMatrix, PopMatrix, Line, Triangle, \
    InstructionGroup
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, OptionProperty, ListProperty, BooleanProperty
from kivy.clock import Clock, mainthread
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
import sender_http
import time
import threading
import math


# Пользовательская кнопка с изменяемым цветом при нажатии
class CustomButton(Button):
    normal_color = ListProperty([0.95, 0.95, 0.95, 1])
    down_color = ListProperty([0.85, 0.85, 0.85, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = self.normal_color
        self.bind(on_press=self.on_button_press)
        self.bind(on_release=self.on_button_release)

    def on_button_press(self, instance):
        self.background_color = self.down_color

    def on_button_release(self, instance):
        self.background_color = self.normal_color


class RoadWidget(Widget):
    text = StringProperty("")
    orientation = OptionProperty("horizontal", options=["horizontal", "vertical"])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self.update_canvas,
            size=self.update_canvas,
            text=self.update_canvas,
            orientation=self.update_canvas,
        )
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        with self.canvas:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=self.pos, size=(self.width, self.height))
            self.draw_text()

    def draw_text(self):
        if not self.text:
            return

        label = CoreLabel(text=self.text, font_size=dp(12), color=(0, 0, 0, 1))
        label.refresh()
        texture = label.texture

        if not texture:
            return

        Color(0, 0, 0, 1)
        if self.orientation == "horizontal":
            # Увеличиваем отступ для текста
            text_x = self.x + (self.width - texture.width) / 2
            text_y = self.y + (self.height - texture.height) / 2 + dp(15)  # Добавляем отступ
            Rectangle(texture=texture, pos=(text_x, text_y), size=texture.size)
        else:
            # Увеличиваем отступ для текста
            text_x = self.x + (self.width - texture.height) / 2
            text_y = self.y + (self.height - texture.width) / 2 + dp(15)  # Добавляем отступ
            PushMatrix()
            Rotate(angle=-90, origin=(text_x, text_y))
            Rectangle(texture=texture, pos=(text_x, text_y), size=texture.size)
            PopMatrix()


class AreaWidget(Widget):
    text = StringProperty("")
    value = NumericProperty(0)
    index = NumericProperty(0)
    max_value = NumericProperty(30)  # Добавлено свойство максимальной заполненности

    def __init__(self, **kwargs):
        super(AreaWidget, self).__init__(**kwargs)
        self.bind(
            pos=self.update_elements,
            size=self.update_elements,
            value=self.update_color_and_text,
        )

        with self.canvas.before:
            # Основной цвет
            self.bg_color = Color(0.85, 0.92, 1, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[20, ]
            )

            # Черная обводка (линия)
            self.outline_color = Color(0, 0, 0, 1)
            self.outline = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, 20),
                width=1  # Толщина обводки
            )

        self.label = Label(
            color=(0.1, 0.1, 0.1, 1),
            font_size=dp(24),
            halign='center',
            valign='middle'
        )
        self.bind(text=self.label.setter('text'))
        self.add_widget(self.label)
        self.update_color_and_text()

    @mainthread
    def update_color_and_text(self, *args):
        self.text = f"{self.value}/{self.max_value}"  # Используем max_value
        percent = (self.value / self.max_value) * 100  # Используем max_value

        if percent > 75:
            self.bg_color.rgba = (1, 0.8, 0.8, 1)
        elif percent < 35:
            self.bg_color.rgba = (0.8, 1, 0.8, 1)
        else:
            self.bg_color.rgba = (1, 0.9, 0.7, 1)
        self.canvas.before.flag_update()

    def update_elements(self, *args):
        # Обновляем основной прямоугольник
        self.rect.pos = self.pos
        self.rect.size = self.size

        # Обновляем обводку
        self.outline.rounded_rectangle = (self.x, self.y, self.width, self.height, 20)

        # Обновляем позицию текста
        self.label.pos = self.pos
        self.label.size = self.size
        self.label.text_size = self.size


class BuildingWidget(Widget):
    text = StringProperty("")
    bg_color = ListProperty([0.85, 0.92, 1, 1])

    def __init__(self, **kwargs):
        super(BuildingWidget, self).__init__(**kwargs)
        self.bind(
            pos=self.update_canvas,
            size=self.update_canvas,
            text=self.update_canvas
        )
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[20, ]
            )
            Color(0, 0, 0, 1)
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, 20),
                width=1
            )

        # Создаем или обновляем текстовую метку
        if not hasattr(self, 'label'):
            self.label = Label(
                text=self.text,
                color=(0.1, 0.1, 0.1, 1),
                font_size=dp(24),
                halign='center',
                valign='middle',
                size=self.size,
                pos=self.pos
            )
            self.add_widget(self.label)
        else:
            self.label.text = self.text
            self.label.pos = self.pos
            self.label.size = self.size


class ParkingScreen(Screen):
    def __init__(self, name, **kwargs):
        super().__init__(name=name, **kwargs)
        self.scheme_mode = False
        self.arrow_group = None  # Группа для хранения стрелок
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()

        main_layout = BoxLayout(orientation='vertical', spacing=dp(10))

        # Общая заполненность
        self.total_label = Label(
            text="Общая заполненность: 0/110",  # Обновлено на общую вместимость
            font_size=dp(18),
            bold=True,
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, None),
            height=dp(40),
            halign='center',
            valign='middle'
        )
        main_layout.add_widget(self.total_label)

        # Контейнер для контента
        self.content_container = BoxLayout(orientation='vertical', size_hint=(1, 1))
        main_layout.add_widget(self.content_container)

        # Кнопки
        button_container = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=dp(10))

        back_button = CustomButton(
            text="Назад в меню",
            normal_color=(0.95, 0.95, 0.95, 1),
            down_color=(0.85, 0.85, 0.85, 1),
            color=(0.1, 0.1, 0.1, 1)
        )
        back_button.bind(on_press=self.switch_to_main)

        self.scheme_button = CustomButton(
            text="Показать схему" if not self.scheme_mode else "Показать парковки",
            normal_color=(0.95, 0.95, 0.95, 1),
            down_color=(0.85, 0.85, 0.85, 1),
            color=(0.1, 0.1, 0.1, 1)
        )
        self.scheme_button.bind(on_press=self.toggle_scheme)

        button_container.add_widget(back_button)
        button_container.add_widget(self.scheme_button)
        main_layout.add_widget(button_container)

        self.add_widget(main_layout)

        # Инициализируем правильный режим
        if self.scheme_mode:
            self.build_scheme()
        else:
            self.build_parking()

        # Запускаем обновление данных
        Clock.schedule_interval(self.update_data, 5)
        self.update_data(0)

    def on_pre_enter(self, *args):
        # Гарантируем правильное отображение при входе
        self.build_ui()

    def switch_to_main(self, instance):
        self.manager.current = 'main'

    def toggle_scheme(self, instance):
        self.scheme_mode = not self.scheme_mode
        self.scheme_button.text = "Показать парковки" if self.scheme_mode else "Показать схему"
        self.build_ui()

    def build_parking(self):
        self.content_container.clear_widgets()
        container = BoxLayout(orientation='horizontal', spacing=dp(10))
        self.content_container.add_widget(container)

        left_column = BoxLayout(orientation='vertical', spacing=dp(5), size_hint=(0.9, 1))
        container.add_widget(left_column)

        # Создаем виджеты для парковки
        top_area = AreaWidget(size_hint=(1, 0.3))
        top_area.index = 2
        top_area.max_value = 15  # Установка максимальной заполненности
        left_column.add_widget(top_area)

        middle_layout = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint=(1, 0.4))
        # Левая область (индекс 0)
        left_area = AreaWidget(size_hint=(1, 1))
        left_area.index = 0
        left_area.max_value = 45  # Установка максимальной заполненности
        middle_layout.add_widget(left_area)

        # Правая область (индекс 1)
        right_area = AreaWidget(size_hint=(1, 1))
        right_area.index = 1
        right_area.max_value = 35  # Установка максимальной заполненности
        middle_layout.add_widget(right_area)
        left_column.add_widget(middle_layout)

        bottom_area = AreaWidget(size_hint=(1, 0.3))
        bottom_area.index = 3
        bottom_area.max_value = 15  # Установка максимальной заполненности
        left_column.add_widget(bottom_area)

        # Дорога справа
        right_road = RoadWidget(
            orientation='vertical',
            text="ул.Мира",
            size_hint=(0.05, 1)
        )
        container.add_widget(right_road)

        # Сохраняем виджеты для обновления данных
        self.areas = [top_area, left_area, right_area, bottom_area]

    def build_scheme(self):
        self.content_container.clear_widgets()
        container = FloatLayout(size_hint=(1, 1))
        self.content_container.add_widget(container)
        self.arrow_group = None  # Сбрасываем группу стрелок

        # Дорога справа (увеличена в 3 раза)
        self.road = RoadWidget(
            orientation='vertical',
            text="ул.Мира",
            size_hint=(0.15, 1),  # Было 0.05
            pos_hint={'right': 1, 'y': 0}
        )
        container.add_widget(self.road)

        # Верхнее здание (ширина уменьшена под новую дорогу)
        top_building = BuildingWidget(
            text="ИнМТ\n(Мира 28)",
            size_hint=(0.85, 0.2),  # Было 0.95
            pos_hint={'x': 0, 'top': 1}
        )
        container.add_widget(top_building)

        # Парковка (ширина уменьшена под новую дорогу)
        self.parking = BuildingWidget(
            text="Парковка",
            size_hint=(0.85, 0.6),  # Было 0.95
            pos_hint={'x': 0, 'center_y': 0.5},
            bg_color=(0.7, 0.8, 0.9, 1)
        )
        container.add_widget(self.parking)

        # Нижнее здание (ширина уменьшена под новую дорогу)
        bottom_building = BuildingWidget(
            text="IRIT-RTF\n(Мира 32)",
            size_hint=(0.85, 0.2),  # Было 0.95
            pos_hint={'x': 0, 'y': 0}
        )
        container.add_widget(bottom_building)

        # Привязываем обновление стрелок к изменению размера контейнера
        container.bind(size=self.update_arrows)
        container.bind(pos=self.update_arrows)

        # Отложенное создание стрелок
        Clock.schedule_once(lambda dt: self.update_arrows(container), 0.1)

    def update_arrows(self, container, *args):
        # Удаляем предыдущую группу стрелок, если она существует
        if self.arrow_group is not None:
            container.canvas.after.remove(self.arrow_group)
            self.arrow_group = None

        # Пропускаем обновление, если дорога еще не инициализирована
        if not hasattr(self, 'road') or self.road.width == 0 or self.road.height == 0:
            return

        # Создаем новую группу для стрелок
        self.arrow_group = InstructionGroup()

        # Добавляем цвет для всех стрелок
        self.arrow_group.add(Color(0.3, 0.3, 0.3, 1))  # Более темный цвет для лучшей видимости

        # Рассчитываем размеры относительно размера экрана
        scale_factor = min(container.width, container.height) / 800
        base_line_width = max(4, 4 * scale_factor)  # Более толстые линии
        arrow_head_size = max(20, 20 * scale_factor)  # Увеличенный размер стрелок

        # Оставляем только две позиции: верх (20%) и низ (80%)
        positions = [0.2, 0.8]

        for i, pos in enumerate(positions):
            # Координаты центра дороги
            road_center_x = self.road.center_x
            arrow_y = (self.road.y + self.road.height * pos)

            if i == 1:  # Нижняя стрелка - поворачивающая к парковке
                # Вертикальная часть
                vertical_end_y = arrow_y - container.height * 0.15
                self.arrow_group.add(Line(
                    points=[
                        road_center_x - dp(15), arrow_y,
                        road_center_x - dp(15), vertical_end_y
                    ],
                    width=base_line_width)
                )

                # Горизонтальная часть
                horizontal_end_x = road_center_x - self.road.width * 1.5
                self.arrow_group.add(Line(
                    points=[
                        road_center_x - dp(15), vertical_end_y,
                        horizontal_end_x , vertical_end_y
                    ],
                    width=base_line_width)
                )

                # Голова стрелки в конце горизонтальной линии (направлена влево)
                # Уменьшаем линию на размер стрелки, чтобы они не накладывались
                adjusted_end_x = horizontal_end_x - arrow_head_size / 2
                self.arrow_group.add(Line(
                    points=[
                        road_center_x - dp(15), vertical_end_y,
                        adjusted_end_x, vertical_end_y
                    ],
                    width=base_line_width)
                )

                # Рисуем треугольник (острие влево)
                self.arrow_group.add(Triangle(
                    points=[
                        horizontal_end_x-dp(20), vertical_end_y,  # Острие
                        horizontal_end_x + arrow_head_size, vertical_end_y - arrow_head_size,
                        horizontal_end_x + arrow_head_size, vertical_end_y + arrow_head_size
                    ])
                )
            else:  # Верхняя стрелка - обычная вниз
                # Тело стрелки (укорачиваем на размер стрелки)
                end_y = arrow_y - container.height * 0.1 + arrow_head_size / 2
                self.arrow_group.add(Line(
                    points=[
                        road_center_x, arrow_y,
                        road_center_x, end_y
                    ],
                    width=base_line_width)
                )

                # Голова стрелки внизу (направлена вниз)
                # Острие находится в конце линии
                self.arrow_group.add(Triangle(
                    points=[
                        road_center_x, (end_y ) - dp(20),  # Острие
                                       road_center_x - arrow_head_size, end_y + arrow_head_size / 1.5,
                                       road_center_x + arrow_head_size, end_y + arrow_head_size / 1.5
                    ])
                )

        # Добавляем группу на холст
        container.canvas.after.add(self.arrow_group)

    def update_data(self, dt):
        threading.Thread(target=self._update_data_background, daemon=True).start()

    def _update_data_background(self):
        try:
            response = sender_http.get_regions_status()
            if response.get('success', False):
                data = response.get('data', [])
                self._update_ui(data)
        except Exception as e:
            print(f"Error updating parking data: {e}")

    @mainthread
    def _update_ui(self, data):
        if not self.scheme_mode:  # Обновляем только в режиме парковок
            total_occupied = 0
            for area in self.areas:
                if area.index < len(data):
                    area.value = data[area.index].get('occupied', 0)
                    total_occupied += area.value
            # Обновляем общую заполненность (сумма максимальных значений = 15+15+45+35=110)
            self.update_total_display(total_occupied)

    @mainthread
    def update_total_display(self, total):
        self.total_label.text = f"Общая заполненность: {total}/110"  # Обновлено на общую вместимость


class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name='main', **kwargs)
        self.parkings = {
            "RTF": {"total": 110, "screen": "rtf"},  # Общая вместимость 110
        }

        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        header = Label(
            text="Главное меню парковок",
            font_size=dp(28),
            bold=True,
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, 0.2))
        layout.add_widget(header)

        for name, data in self.parkings.items():
            btn = CustomButton(
                text=f"{name}\nСвободно: {data['total']}",  # Используем сохраненное значение
                markup=True,
                font_size=dp(20),
                normal_color=(0.95, 0.95, 0.95, 1),
                down_color=(0.85, 0.85, 0.85, 1),
                color=(0.1, 0.1, 0.1, 1),
                size_hint=(1, 0.3)
            )
            btn.bind(on_press=lambda x, s=data['screen']: self.switch_to_parking(s))
            layout.add_widget(btn)

        self.add_widget(layout)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        Clock.schedule_interval(self.update_totals, 5)

    def _update_bg(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def update_totals(self, dt):
        threading.Thread(target=self._update_totals_background, daemon=True).start()

    def _update_totals_background(self):
        try:
            response = sender_http.get_regions_status()
            if response.get('success', False):
                data = response.get('data', [])
                # Общая вместимость парковки 110
                total_occupied = sum(region.get('occupied', 0) for region in data[:4])
                total_free = 110 - total_occupied  # Рассчитываем свободные места
                self._update_ui(total_free)
        except Exception as e:
            print(f"Error updating totals: {e}")

    @mainthread
    def _update_ui(self, total_free):
        self.update_parking_free('RTF', total_free)

    @mainthread
    def update_parking_free(self, parking_name, total_free):
        # Обновляем общее количество свободных мест
        self.parkings[parking_name]["total"] = total_free
        for child in self.children[0].children:
            if isinstance(child, CustomButton) and parking_name in child.text:
                child.text = f"{parking_name}\nСвободно: {total_free}"

    def switch_to_parking(self, screen_name):
        self.manager.current = screen_name


class ParkingApp(App):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)

        sm = ScreenManager()

        with sm.canvas.before:
            Color(1, 1, 1, 1)
            sm.bg_rect = Rectangle(size=sm.size, pos=sm.pos)
        sm.bind(size=self._update_sm_bg, pos=self._update_sm_bg)

        sm.add_widget(MainMenuScreen())
        sm.add_widget(ParkingScreen(name='rtf'))
        return sm

    def _update_sm_bg(self, instance, value):
        instance.bg_rect.size = instance.size
        instance.bg_rect.pos = instance.pos


if __name__ == '__main__':
    ParkingApp().run()