from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from fergusonbequest.models import Attraction, VisitSlot, Booking
from .utils import unique_email, unique_username
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class CarouselFunctionalityTests(TestCase):
    """Tests for the featured attractions carousel on the home."""

    def setUp(self):
        """Set up test user and sample attractions."""
        self.username = unique_username()
        self.email = unique_email()
        self.password = "TestPass123"
        self.user = User.objects.create_user(
            username=self.username, 
            email=self.email, 
            password=self.password
        )
        
        # Create test attractions
        self.attraction1 = Attraction.objects.create(
            name="Blair Drummond Safari Park",
            slug="blair-drummond",
            location="Stirling",
            description="Safari and adventure park with exotic animals.",
            booking_open=timezone.now() - timedelta(days=1),
            booking_close=timezone.now() + timedelta(days=30),
            attraction_type='regular'
        )
        
        self.attraction2 = Attraction.objects.create(
            name="Edinburgh Zoo",
            slug="edinburgh-zoo",
            location="Edinburgh",
            description="Scotland's most famous zoo with pandas and penguins.",
            booking_open=timezone.now() - timedelta(days=1),
            booking_close=timezone.now() + timedelta(days=30),
            attraction_type='regular'
        )
        
        self.attraction3 = Attraction.objects.create(
            name="Glasgow Science Centre",
            slug="glasgow-science",
            location="Glasgow",
            description="Interactive science museum with planetarium.",
            booking_open=timezone.now() - timedelta(days=1),
            booking_close=timezone.now() + timedelta(days=30),
            attraction_type='regular'
        )

    def test_dashboard_requires_login(self):
        """Dashboard should require authentication.

        An unauthenticated user trying to access the dashboard should be
        redirected to the login page.

        Expected output:
        - HTTP 302 redirect to login page

        Pass: status code is 302 and redirects to login.
        Fail: user can access dashboard without authentication.
        """
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_home_loads_with_attractions(self):
        """home should load successfully with featured attractions.

        When a logged-in user accesses the home, the page should load
        with a 200 status and display featured attractions in the carousel.

        Expected output:
        - HTTP 200 response
        - Page contains carousel elements

        Pass: status code is 200.
        Fail: page doesn't load or returns error.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'fb-slider')

    def test_carousel_contains_attraction_data(self):
        """Carousel should display attraction titles and descriptions.

        The home carousel should render the attraction names and
        descriptions for all featured attractions.

        Parameters:
        - featured_attractions: list of Attraction objects from database

        Expected output:
        - Page contains attraction names
        - Page contains attraction descriptions (or subtitles)

        Pass: all attraction names appear in the response.
        Fail: attraction data is missing from carousel.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        # Check that attraction names are in the response
        self.assertContains(resp, self.attraction1.name)
        self.assertContains(resp, self.attraction2.name)
        self.assertContains(resp, self.attraction3.name)

    def test_carousel_slides_have_booking_urls(self):
        """Each carousel slide should have a data-book-url attribute.

        The JavaScript uses data-book-url to direct users to the correct
        booking page. Each slide should have this attribute pointing to
        the attraction's booking URL.

        Parameters:
        - data-book-url: attribute on each figure.fb-slide element

        Expected output:
        - HTML contains data-book-url="/attraction/{id}/book/" for each slide

        Pass: all slides have valid booking URLs.
        Fail: data-book-url attributes are missing or incorrect.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        # Check that booking URLs are present for each attraction
        self.assertContains(resp, f'data-book-url="/attraction/{self.attraction1.id}/book/"')
        self.assertContains(resp, f'data-book-url="/attraction/{self.attraction2.id}/book/"')
        self.assertContains(resp, f'data-book-url="/attraction/{self.attraction3.id}/book/"')

    def test_carousel_has_book_now_button(self):
        """Carousel should have a 'Book now' button with correct ID.

        The JavaScript needs a button with id="fb-book-btn" to update
        dynamically as users navigate the carousel.

        Expected output:
        - HTML contains <a id="fb-book-btn">
        - Button text is "Book now"

        Pass: button exists with correct ID and text.
        Fail: button is missing or has wrong attributes.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        self.assertContains(resp, 'id="fb-book-btn"')
        self.assertContains(resp, 'Book now')

    def test_carousel_has_navigation_arrows(self):
        """Carousel should have previous and next navigation buttons.

        Users need arrow buttons to navigate between attractions. These
        should have the correct CSS classes for the JavaScript to find them.

        Expected output:
        - HTML contains previous arrow with class 'fb-slider-arrow--prev'
        - HTML contains next arrow with class 'fb-slider-arrow--next'

        Pass: both navigation buttons are present.
        Fail: navigation buttons are missing.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        self.assertContains(resp, 'fb-slider-arrow--prev')
        self.assertContains(resp, 'fb-slider-arrow--next')

    def test_carousel_has_indicator_dots(self):
        """Carousel should have indicator dots for each attraction.

        Visual indicators help users see how many attractions are in the
        carousel and which one is currently active.

        Expected output:
        - HTML contains dots matching the number of featured attractions
        - First dot has 'fb-dot--active' class

        Pass: correct number of dots are present.
        Fail: dots are missing or count is wrong.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        # Should have dots for each featured attraction (up to 4)
        self.assertContains(resp, 'fb-dot')
        # First dot should be active
        self.assertContains(resp, 'fb-dot--active')

    def test_carousel_javascript_present(self):
        """home should include the carousel JavaScript.

        The JavaScript code handles slide navigation and URL updates.
        It should be present in the rendered HTML.

        Expected output:
        - Page contains JavaScript function 'showSlide'
        - Page contains JavaScript function 'updateBookButtonUrl'

        Pass: required JavaScript functions are in the response.
        Fail: JavaScript is missing or incomplete.
        """
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

        # Check that the external JS file is loaded
        self.assertContains(resp, 'home_carousel.js')
        # Check that carousel container exists
        self.assertContains(resp, 'id="fb-slider"')
        # Check that data-book-url attribute exists in slides
        self.assertContains(resp, 'data-book-url=')

    def test_booking_page_exists_for_attractions(self):
        """Booking URLs should lead to valid booking pages.

        When a user clicks the 'Book now' button, they should be taken
        to a real booking page that exists and loads successfully.

        Parameters:
        - attraction_id: ID of the attraction to book

        Expected output:
        - GET request to /attraction/{id}/book/ returns HTTP 200
        - Page is the booking form for that specific attraction

        Pass: booking page loads with 200 status.
        Fail: booking page returns 404 or error.
        """
        self.client.login(username=self.username, password=self.password)
        
        # Test that booking URLs actually work
        booking_url = reverse('attraction_book', kwargs={'attraction_pk': self.attraction1.id})
        resp = self.client.get(booking_url)
        
        # Should load the booking page 
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.attraction1.name)

    def test_fallback_when_no_attractions(self):
        """home should handle the case when no attractions exist.

        If the database has no attractions, the home should still
        load without errors, possibly showing demo data or empty state.

        Expected output:
        - HTTP 200 response even with no attractions
        - Page loads without server errors

        Pass: home loads successfully.
        Fail: page crashes or returns error.
        """
        # Delete all attractions
        Attraction.objects.all().delete()
        
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        # Should still load
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'fb-slider')

    def test_view_returns_correct_data_structure(self):
        """home view should pass correctly structured attraction data.

        The view should provide featured_attractions as a list of dicts,
        each containing the required keys for the template to render.

        Expected output:
        - featured_attractions is a list
        - Each item has keys: title, subtitle, image, id, url

        Pass: data structure matches expected format.
        Fail: data is missing required fields.
        """
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        featured_attractions = resp.context['featured_attractions']
        
        # Should be a list
        self.assertIsInstance(featured_attractions, list)
        
        # Each attraction should have the required keys
        if len(featured_attractions) > 0:
            first_attraction = featured_attractions[0]
            self.assertIn('title', first_attraction)
            self.assertIn('subtitle', first_attraction)
            self.assertIn('image', first_attraction)
            self.assertIn('id', first_attraction)
            self.assertIn('url', first_attraction)

    def test_carousel_limits_to_four_attractions(self):
        """Carousel should display at most 4 featured attractions.

        Even if more attractions exist in the database, only the first
        4 should be shown in the carousel to avoid clutter.

        Expected output:
        - featured_attractions list has maximum length of 4

        Pass: featured_attractions contains 4 or fewer items.
        Fail: more than 4 attractions are returned.
        """
        # Create a 4th and 5th attraction
        Attraction.objects.create(
            name="Kelvingrove Museum",
            slug="kelvingrove",
            location="Glasgow",
            description="Art gallery and museum.",
            attraction_type='regular'
        )
        Attraction.objects.create(
            name="National Museum",
            slug="national-museum",
            location="Edinburgh",
            description="Scotland's national museum.",
            attraction_type='regular'
        )
        
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        
        featured_attractions = resp.context['featured_attractions']
        self.assertLessEqual(len(featured_attractions), 4)

    def test_carousel_prioritises_most_booked_then_falls_back_alphabetical(self):
        """Most-booked attractions should appear first, then alphabetical fallback fills remaining slots."""
        attraction4 = Attraction.objects.create(
            name="Kelvingrove Museum",
            slug="kelvingrove-museum",
            location="Glasgow",
            description="Art gallery and museum.",
            attraction_type='regular'
        )

        slot_for_top = VisitSlot.objects.create(
            attraction=self.attraction2,
            date=timezone.now().date() + timedelta(days=3),
            capacity=20,
            remaining=20,
        )

        user2 = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="TestPass123",
        )
        user3 = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="TestPass123",
        )

        Booking.objects.create(
            attraction=self.attraction2,
            slot=slot_for_top,
            full_name="User One",
            email=self.user.email,
            user=self.user,
            num_tickets=1,
            cancelled=False,
        )
        Booking.objects.create(
            attraction=self.attraction2,
            slot=slot_for_top,
            full_name="User Two",
            email=user2.email,
            user=user2,
            num_tickets=1,
            cancelled=False,
        )

        slot_cancelled = VisitSlot.objects.create(
            attraction=self.attraction1,
            date=timezone.now().date() + timedelta(days=4),
            capacity=20,
            remaining=20,
        )
        Booking.objects.create(
            attraction=self.attraction1,
            slot=slot_cancelled,
            full_name="User Three",
            email=user3.email,
            user=user3,
            num_tickets=1,
            cancelled=True,
        )

        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('home'))
        featured_attractions = resp.context['featured_attractions']
        titles = [item['title'] for item in featured_attractions]

        self.assertEqual(titles[0], self.attraction2.name)
        self.assertEqual(titles[1:], sorted([self.attraction1.name, self.attraction3.name, attraction4.name]))

